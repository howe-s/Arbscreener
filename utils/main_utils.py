from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from collections import Counter, defaultdict
from sqlalchemy.orm import sessionmaker
from utils.models import Contracts, User, Purchase  # Ensure these are correctly imported
from dexscreener import DexscreenerClient
import time
from functools import wraps, lru_cache
from typing import Union, List
import random
import requests
from flask import Flask, current_app
from utils.models import db

client = DexscreenerClient()
session = db.session

api_call_counter = Counter()

def safe_get(obj, attr, default=None):
    """Helper function to safely access an attribute or return a default value."""
    try:
        return getattr(obj, attr, default) if obj is not None else default
    except AttributeError:
        return default


requests_this_minute = 0
last_reset_time = 0



def retry_with_backoff(func, max_retries=3, initial_delay=1, backoff_factor=2):
    """
    Decorator to retry API calls with exponential backoff in case of rate limiting.
    """
    def wrapper(*args, **kargs):
        retries = 0
        while retries < max_retries:
            try:
                return func(*args, **kargs)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    delay = initial_delay * (backoff_factor ** retries) + random.uniform(0, 1)
                    time.sleep(delay)
                    retries += 1
                else:
                    raise
        return None  # or handle as appropriate if all retries fail
    return wrapper

seen_addresses = defaultdict(bool)


@retry_with_backoff
def rate_limited(max_calls_per_minute):
    def decorator(func):
        def wrapper(*args, **kwargs):
            global requests_this_minute, last_reset_time
            current_time = time.time()
            
            # Reset counter if a minute has passed
            if current_time - last_reset_time >= 60:
                requests_this_minute = 0
                last_reset_time = current_time
            
            # Increment counter and check limit
            requests_this_minute += 1
            if requests_this_minute > max_calls_per_minute:
                # If limit is exceeded, wait until the next minute
                sleep_time = 60 - (current_time - last_reset_time)
                sleep(sleep_time)
                requests_this_minute = 1
                last_reset_time = time.time()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

@retry_with_backoff
@rate_limited(60)  # Adjust rate limiting as needed
def fetch_and_cache_pairs(session, contract: Union[str, List[str]]):
    """
    Fetch pairs with rate limiting, caching, and address checking.
    """
    if isinstance(contract, list):
        search_query = ", ".join(contract)
    else:
        search_query = contract

    try:
        search_results = client.search_pairs(search_query)
        if search_results:
            for pair in search_results:
                contract_address = pair.pair_address      
                existing_contract = db.session.query(Contracts).filter_by(contract_address=contract_address).first()
                if not existing_contract:
                    new_contract = Contracts(
                        contract_address=contract_address,
                        base_token_address=pair.base_token.address,
                        quote_token_address=pair.quote_token.address,
                        chain_id=pair.chain_id,
                        dex_id=pair.dex_id,                        
                        price_native=float(pair.price_native) if pair.price_native is not None else 0.0
                        
                    )
                    db.session.add(new_contract)
                    logging.info(f"Saved contract address: {contract_address}, price_native: {new_contract.price_native}")
            db.session.commit()  
            
            # Mark as seen after successful processing
            for addr in search_query.split(', ') if isinstance(contract, list) else [search_query]:
                seen_addresses[addr] = True
            # print(search_results)
            return search_results
    except Exception as e:
        logging.error(f"Error in fetch_and_cache_pairs with query {search_query}: {e}")
        return None
    
def process_token_pairs(search):
    token_pairs = []
    for TokenPair in search:        
        liquidity = TokenPair.liquidity if TokenPair.liquidity is not None else {}
        
        token_pairs.append({
            'pair': safe_get(TokenPair.base_token, 'name', 'N/A') + '/' + safe_get(TokenPair.quote_token, 'name', 'N/A'),
            'pool_address': safe_get(TokenPair, 'pair_address', 'N/A'),
            'pool_url': safe_get(TokenPair, 'url', 'N/A'),
            'price_usd': safe_get(TokenPair, 'price_usd', 0.0),
            'price_native': safe_get(TokenPair, 'price_native', 0.0),
            'liquidity_usd': safe_get(liquidity, 'usd', 0.0),
            'liquidity_base': safe_get(liquidity, 'base', 0.0),
            'liquidity_quote': safe_get(liquidity, 'quote', 0.0),
            'baseToken_address': safe_get(TokenPair.base_token, 'address', 'N/A'),
            'quoteToken_address': safe_get(TokenPair.quote_token, 'address', 'N/A'),
            'chain_id': safe_get(TokenPair, 'chain_id', 'N/A'),
            'dex_id': safe_get(TokenPair, 'dex_id', 'N/A'),
            'baseToken_name': safe_get(TokenPair.base_token, 'name', 'N/A'),
            'quoteToken_Name': safe_get(TokenPair.quote_token, 'name', 'N/A')
        })
    return token_pairs

def calculate_arbitrage_profit(initial_investment, price_pair1, price_pair2, slippage, fee_percentage, liquidity_pair1, liquidity_pair2):
    # Convert initial investment to amount in pair1
    amount_pair1 = initial_investment / price_pair1
    
    # Simplified slippage model
    def apply_slippage(amount, liquidity, slippage):
        return amount * (1 - slippage * (amount / float(liquidity)))  # Convert liquidity to float to ensure arithmetic operation works
    
    adjusted_amount_pair1 = apply_slippage(amount_pair1, liquidity_pair1, slippage)
    value_pair2 = adjusted_amount_pair1 * price_pair2
    final_amount_pair2 = apply_slippage(value_pair2, liquidity_pair2, slippage)
    
    # Calculate fees
    fees = initial_investment * fee_percentage * 2  # Considering two trades for fees
    
    # Profit calculation
    profit = final_amount_pair2 - initial_investment - fees
    
    return profit

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_arbitrage_opportunities(token_pairs, slippage, fee_percentage, initial_investment, user_purchases):
    logging.info('Starting arbitrage opportunity detection')
    arbitrage_opportunities = []
    total_pairs_checked = 0
    
    for i, pair1 in enumerate(token_pairs):
        for j, pair2 in enumerate(token_pairs):
            if i != j:  # Ensure pairs are different
                total_pairs_checked += 1
                # Check if pairs share a common token
                if (pair1['baseToken_address'] == pair2['baseToken_address'] or 
                    pair1['baseToken_address'] == pair2['quoteToken_address'] or 
                    pair1['quoteToken_address'] == pair2['baseToken_address']):
                    
                    logging.debug(f'Checking pair combination: {pair1["pair"]} and {pair2["pair"]}')
                    
                    # Determine price for comparison based on token matching
                    if pair1['baseToken_address'] == pair2['baseToken_address']:
                        pair1_price = float(pair1['price_native'])
                        pair2_price = float(pair2['price_native'])
                    elif pair1['baseToken_address'] == pair2['quoteToken_address']:
                        pair1_price = float(pair1['price_native'])
                        pair2_price = 1 / float(pair2['price_native'])  # Invert price since we're comparing base to quote
                    elif pair1['quoteToken_address'] == pair2['baseToken_address']:
                        pair1_price = 1 / float(pair1['price_native'])  # Invert price since we're comparing quote to base
                        pair2_price = float(pair2['price_native'])
                    else:
                        logging.debug(f'Skipping pair combination as no common token found for {pair1["pair"]} and {pair2["pair"]}')
                        continue  # This shouldn't happen due to our condition above, but added for robustness

                    # Check for sufficient liquidity
                    if float(pair1['liquidity_usd']) > 10000 and float(pair2['liquidity_usd']) > 10000:
                        
                        price_diff = pair2_price - pair1_price
                        liquidity_diff = float(pair1['liquidity_usd']) - float(pair2['liquidity_usd'])

                        # Determine which liquidity to use based on the direction of the arbitrage
                        if price_diff > 0:
                            # We use the liquidity of the token common in both pairs for base liquidity
                            if pair1['baseToken_address'] == pair2['baseToken_address']:
                                base_liquidity = min(float(pair1['liquidity_base']), float(pair2['liquidity_base']))
                            elif pair1['baseToken_address'] == pair2['quoteToken_address']:
                                base_liquidity = min(float(pair1['liquidity_base']), float(pair2['liquidity_quote']))
                            else:  # pair1['quoteToken_address'] == pair2['baseToken_address']
                                base_liquidity = min(float(pair1['liquidity_quote']), float(pair2['liquidity_base']))
                            
                            profit = calculate_arbitrage_profit(initial_investment, 
                                                                pair1_price, 
                                                                pair2_price, 
                                                                slippage,                                                                 
                                                                fee_percentage,
                                                                float(pair1['liquidity_base']) if pair1['baseToken_address'] in [pair2['baseToken_address'], pair2['quoteToken_address']] else float(pair1['liquidity_quote']),
                                                                float(pair2['liquidity_base']) if pair2['baseToken_address'] in [pair1['baseToken_address'], pair1['quoteToken_address']] else float(pair2['liquidity_quote']))
                            
                            if profit > 0:  # Only consider positive profit opportunities
                                logging.info(f'Found potential arbitrage opportunity: {pair1["pair"]} and {pair2["pair"]}')
                                int_profit = int(profit * 10**8) / 10**8
                                
                                opportunity = {
                                    'pair1': pair1['pair'],
                                    'pair1_price': pair1['price_usd'],
                                    'pair1_price_round': f"{round(pair1['price_usd'], 8)}",
                                    'pair1_liquidity': f"${pair1['liquidity_usd']:,.2f}",
                                    'pair1_liquidity_base': f"{pair1['liquidity_base']:,.2f}",
                                    'pair1_liquidity_quote': f"{pair1['liquidity_quote']:,.2f}",
                                    'pool_pair1_address': pair1['pool_address'],
                                    'pair1_baseToken_address': pair1['baseToken_address'],
                                    'pair1_quoteToken_address': pair1['quoteToken_address'],
                                    'pool_pair1_url': pair1['pool_url'],
                                    'pair2': pair2['pair'],
                                    'pair2_price': pair2['price_usd'],
                                    'pair2_price_round': f"{round(pair2['price_usd'], 8)}",
                                    'pair2_liquidity': f"${pair2['liquidity_usd']:,.2f}",
                                    'pair2_liquidity_base': f"{pair2['liquidity_base']:,.2f}",
                                    'pair2_liquidity_quote': f"{pair2['liquidity_quote']:,.2f}",
                                    'pool_pair2_address': pair2['pool_address'],  
                                    'pair2_baseToken_address': pair2['baseToken_address'],
                                    'pair2_quoteToken_address': pair2['quoteToken_address'],
                                    'pool_pair2_url': pair2['pool_url'],
                                    'price_diff': f"${price_diff:,.2f}",
                                    'liquidity_diff': f"${liquidity_diff:,.2f}",
                                    'profit': f"${profit:,.2f}",
                                    'int_profit': int_profit,
                                    'potential_profit': f"${base_liquidity * price_diff:,.2f}",
                                    'pair1_chain_id': pair1['chain_id'],
                                    'pair1_dex_id': pair1['dex_id'], 
                                    'pair2_chain_id': pair2['chain_id'],
                                    'pair2_dex_id': pair2['dex_id'],
                                    'pair1_priceNative': pair1['price_native'],
                                    'pair2_priceNative': pair2['price_native'],
                                    'pair1_priceNative_round': f"{round(pair1['price_native'], 8)}",
                                    'pair2_priceNative_round': f"{round(pair2['price_native'], 8)}",
                                    'nativePrice_difference': price_diff,
                                }
                                
                                arbitrage_opportunities.append(opportunity)
                            else:
                                logging.debug(f'No profit for pairs {pair1["pair"]} and {pair2["pair"]}: Profit = ${profit:.2f}')
                        else:
                            logging.debug(f'Price difference not positive for {pair1["pair"]} and {pair2["pair"]}: {price_diff}')
                    else:
                        logging.debug(f'Insufficient liquidity for pair1: {pair1["pair"]} or pair2: {pair2["pair"]}')

    logging.info(f'Checked {total_pairs_checked} pair combinations. Found {len(arbitrage_opportunities)} arbitrage opportunities.')
    return arbitrage_opportunities




# Configure logging if not already done in the module where this function resides
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_third_contract_data(unique_pair_addresses, arbitrage_opportunities, session, initial_investment, slippage, fee_percentage):
    # logging.info('Starting to find third contract data')
    third_pair_index = {}  # This will hold either new or cached data
    combined_opportunities = []
    seen_combined_opportunities = set()

    # Fetch or use cached data for third pair
    third_pair_index = fetch_or_use_cached_data(unique_pair_addresses, session)
    
    # logging.info(f'Indexed {len(third_pair_index)} third contracts')

    for opportunity in arbitrage_opportunities:
        logging.debug(f'Processing opportunity for pair1: {opportunity["pair1"]}, pair2: {opportunity["pair2"]}')
        matched_pair = find_matching_third_pair(opportunity, third_pair_index)
        
        if matched_pair:
            combined_opportunity = combine_opportunity_data(opportunity, matched_pair)
            calculate_usd_prices(combined_opportunity)
            calculate_price_discrepancies(combined_opportunity)

            opportunity_key = tuple(sorted([combined_opportunity['pair1'], combined_opportunity['pair2'], combined_opportunity['pair3']]))
            if opportunity_key not in seen_combined_opportunities:
                seen_combined_opportunities.add(opportunity_key)
                combined_opportunities.append(combined_opportunity)
                # logging.info(f'Added opportunity: {combined_opportunity}')
                
                if check_price_compatibility(combined_opportunity, initial_investment, slippage, fee_percentage):
                    combined_opportunities.append(combined_opportunity)
                    # logging.info(f'Added opportunity: {combined_opportunity}')
                else:
                    logging.debug(f'Skipped opportunity due to incompatible price: {combined_opportunity}')
            else:
                logging.debug(f'Skipped duplicate opportunity: {combined_opportunity}')
        else:
            logging.warning(f"No third pair matched for opportunity: {opportunity}")

    # logging.info(f'Final number of arbitrage opportunities with third pair: {len(combined_opportunities)}')
    return combined_opportunities

def fetch_or_use_cached_data(unique_pair_addresses, session):
    third_pair_index = {}
    should_fetch_new_data = check_for_price_change(unique_pair_addresses, session)
    
    if should_fetch_new_data:
        for contract in unique_pair_addresses:
            search = fetch_and_cache_pairs(session, contract)
            if search:
                for pair in search:
                    liquidity_data = safe_get(pair, 'liquidity', {})
                    if hasattr(liquidity_data, 'usd') and liquidity_data.usd > 1:
                        pair_details = create_pair_details(pair)
                        third_pair_index[pair_details['pair_address']] = pair_details
                        update_price_in_db(session, pair_details['pair_address'], pair_details['price_native'])
                        logging.debug(f"Added to third_pair_index: {pair_details}")
            else:
                logging.debug(f'No search results for contract {contract}')
    else:
        for contract in unique_pair_addresses:
            stored_contract = session.query(Contracts).filter_by(contract_address=contract).first()
            if stored_contract:
                third_pair_index[contract] = create_details_from_db(stored_contract)
                logging.debug(f"Using cached data for contract {contract}: {third_pair_index[contract]}")
            else:
                logging.warning(f'No stored data for contract address: {contract}')
    
    return third_pair_index

def check_for_price_change(unique_pair_addresses, session):
    for contract in unique_pair_addresses:
        last_known_price = get_last_known_price(session, contract)
        if last_known_price is None:
            return True
        search = fetch_and_cache_pairs(session, contract)
        if search and any(float(safe_get(pair, 'price_native', 0.0)) != last_known_price for pair in search if safe_get(pair, 'pair_address') == contract):
            return True
    return False

def get_last_known_price(session, contract_address):
    contract = session.query(Contracts).filter_by(contract_address=contract_address).first()
    if contract:
        logging.debug(f"Last known price for {contract_address}: {contract.price_native}")
        return float(contract.price_native) if contract.price_native is not None else None
    else:
        logging.debug(f"No stored data for contract address: {contract_address}")
        return None

def update_price_in_db(session, contract_address, new_price):
    contract = session.query(Contracts).filter_by(contract_address=contract_address).first()
    if contract:
        contract.price_native = float(new_price)
        logging.debug(f"Updated price in DB for {contract_address}: {new_price}")
    else:
        new_contract = Contracts(contract_address=contract_address, price_native=float(new_price))
        session.add(new_contract)
        logging.debug(f"Added new contract to DB: {contract_address} with price: {new_price}")
    session.commit()

def create_pair_details(pair):
    liquidity_data = safe_get(pair, 'liquidity', {})
    return {
        'baseToken_address': safe_get(pair.base_token, 'address', 'N/A'),
        'quoteToken_address': safe_get(pair.quote_token, 'address', 'N/A'),
        'pair_address': safe_get(pair, 'pair_address', 'N/A'),
        'pair': f"{safe_get(pair.base_token, 'name', 'N/A')}/{safe_get(pair.quote_token, 'name', 'N/A')}",
        'price_usd': float(safe_get(pair, 'price_usd', 0.0)),
        'price_native': float(safe_get(pair, 'price_native', 0.0)),
        'liquidity': liquidity_data,
        'url': safe_get(pair, 'url', 'N/A'),
        'chain_id': safe_get(pair, 'chain_id', 'N/A'),
        'dex_id': safe_get(pair, 'dex_id', 'N/A')
    }

def create_details_from_db(stored_contract):
    return {
        'baseToken_address': stored_contract.base_token_address,
        'quoteToken_address': stored_contract.quote_token_address,
        'pair_address': stored_contract.contract_address,
        'pair': f"{stored_contract.base_token_name}/{stored_contract.quote_token_name}",
        'price_usd': stored_contract.price_usd,
        'price_native': stored_contract.price_native,
        'liquidity': {'usd': 0.0, 'base': 0.0, 'quote': 0.0},
        'url': 'N/A',
        'chain_id': stored_contract.chain_id,
        'dex_id': stored_contract.dex_id
    }

def find_matching_third_pair(opportunity, third_pair_index):
    addresses = [
        opportunity['pair1_baseToken_address'],
        opportunity['pair1_quoteToken_address'],
        opportunity['pair2_baseToken_address'],
        opportunity['pair2_quoteToken_address']
    ]
    
    counter = Counter(addresses)
    unique_tokens = [addr for addr, count in counter.items() if count == 1]
    shared_tokens = [addr for addr, count in counter.items() if count > 1]

    if len(unique_tokens) == 2:
        unique_token1, unique_token2 = sorted(unique_tokens)
        for pair_address, pair_data in third_pair_index.items():
            if (pair_data['baseToken_address'] == unique_token1 and pair_data['quoteToken_address'] == unique_token2) or \
               (pair_data['baseToken_address'] == unique_token2 and pair_data['quoteToken_address'] == unique_token1):
                return pair_data
    elif len(unique_tokens) == 1 and len(shared_tokens) == 1:
        unique_token = unique_tokens[0]
        shared_token = shared_tokens[0]
        for pair_address, pair_data in third_pair_index.items():
            if (pair_data['baseToken_address'] == unique_token and pair_data['quoteToken_address'] == shared_token) or \
               (pair_data['baseToken_address'] == shared_token and pair_data['quoteToken_address'] == unique_token):
                return pair_data
    elif len(shared_tokens) == 2:
        shared_token1, shared_token2 = sorted(shared_tokens)
        for pair_address, pair_data in third_pair_index.items():
            if (pair_data['baseToken_address'] == shared_token1 and pair_data['quoteToken_address'] == shared_token2) or \
               (pair_data['baseToken_address'] == shared_token2 and pair_data['quoteToken_address'] == shared_token1):
                return pair_data
    
    return None

def combine_opportunity_data(opportunity, matched_pair):
    combined_opportunity = opportunity.copy()
    combined_opportunity.update({
        'pair3': matched_pair['pair'],
        'pair3_price': matched_pair['price_usd'],
        'pair3_priceNative_round': f"{round(float(matched_pair['price_native']), 8)}",
        'pair3_liquidity': f"${safe_get(matched_pair['liquidity'], 'usd', 0.0):,.2f}",
        'pair3_liquidity_base': f"{safe_get(matched_pair['liquidity'], 'base', 0.0):,.2f}",
        'pair3_liquidity_quote': f"{safe_get(matched_pair['liquidity'], 'quote', 0.0):,.2f}",
        'pool_pair3_address': matched_pair['pair_address'],
        'pair3_baseToken_address': matched_pair['baseToken_address'],
        'pair3_quoteToken_address': matched_pair['quoteToken_address'],
        'pool_pair3_url': matched_pair['url'],
        'pair3_chain_id': matched_pair['chain_id'],
        'pair3_dex_id': matched_pair['dex_id']
    })
    return combined_opportunity

def calculate_usd_prices(combined_opportunity):
    quote_price_usd_1 = float(combined_opportunity['pair1_price']) / float(combined_opportunity['pair1_priceNative_round'])
    quote_price_usd_2 = 1.0 if combined_opportunity['pair2_quoteToken_address'].lower() == 'usd' else float(combined_opportunity['pair2_price']) / float(combined_opportunity['pair2_priceNative_round'])
    quote_price_usd_3 = 1.0 if combined_opportunity['pair3_quoteToken_address'].lower() == 'usd' else float(combined_opportunity['pair3_price']) / float(combined_opportunity['pair3_priceNative_round'])
    
    combined_opportunity['quote_price_usd_1'] = f"${quote_price_usd_1:.2f}"
    combined_opportunity['quote_price_usd_2'] = f"${quote_price_usd_2:.2f}"
    combined_opportunity['quote_price_usd_3'] = f"${quote_price_usd_3:.2f}"

def calculate_price_discrepancies(combined_opportunity):
    # print('COMBINED_OPPORTUNITY~~~~~', combined_opportunity)
    
    # Extract prices for all pairs
    base_price_usd_1 = float(combined_opportunity['pair1_price'])
    base_price_usd_2 = float(combined_opportunity['pair2_price'])
    base_price_usd_3 = float(combined_opportunity['pair3_price']) if 'pair3_price' in combined_opportunity else None

    # Extract quote prices for all pairs
    quote_price_usd_1 = float(combined_opportunity['quote_price_usd_1'][1:])
    quote_price_usd_2 = float(combined_opportunity['quote_price_usd_2'][1:])
    quote_price_usd_3 = float(combined_opportunity['quote_price_usd_3'][1:]) if 'quote_price_usd_3' in combined_opportunity else None

    # Helper function to calculate percentage difference
    def calculate_difference(price1, price2):
        if price1 != 0:
            return f"{(price1 - price2) / price1 * 100:.2f}%"
        else:
            return 'N/A'

    # Function to get the price of a token from another pair
    def get_price_from_pair(token_address, pair_number):
        for token_key, price in [
            ('pair{0}_baseToken_address'.format(pair_number), 'pair{0}_price'.format(pair_number)),
            ('pair{0}_quoteToken_address'.format(pair_number), 'quote_price_usd_{0}'.format(pair_number))
        ]:
            if combined_opportunity.get(token_key) == token_address:
                return float(combined_opportunity[price][1:]) if 'quote' in token_key else float(combined_opportunity[price])
        return None

    # Calculate discrepancies for each token across all pairs
    pairs = ['1', '2', '3']  # Assuming these are the pair numbers you're working with

    # Dictionary to store calculated discrepancies
    discrepancies = {}

    for pair_number in pairs:
        base_token_address = combined_opportunity[f'pair{pair_number}_baseToken_address']
        quote_token_address = combined_opportunity[f'pair{pair_number}_quoteToken_address']
        base_price = float(combined_opportunity[f'pair{pair_number}_price'])
        quote_price = float(combined_opportunity[f'quote_price_usd_{pair_number}'][1:])

        # For base token
        for compare_pair in pairs:
            if pair_number != compare_pair:
                compare_price = get_price_from_pair(base_token_address, compare_pair)
                if compare_price is not None:
                    pair1 = int(pair_number)
                    pair2 = int(compare_pair)
                    discrepancy_key = f'baseToken_difference_{min(pair1, pair2)}{max(pair1, pair2)}'
                    if discrepancy_key not in discrepancies:
                        discrepancies[discrepancy_key] = calculate_difference(base_price, compare_price)
                        print(f"Discrepancy for {discrepancy_key}: {discrepancies[discrepancy_key]}")

        # For quote token
        for compare_pair in pairs:
            if pair_number != compare_pair:
                compare_price = get_price_from_pair(quote_token_address, compare_pair)
                if compare_price is not None:
                    pair1 = int(pair_number)
                    pair2 = int(compare_pair)
                    discrepancy_key = f'quoteToken_difference_{min(pair1, pair2)}{max(pair1, pair2)}'
                    if discrepancy_key not in discrepancies:
                        discrepancies[discrepancy_key] = calculate_difference(quote_price, compare_price)
                        print(f"Discrepancy for {discrepancy_key}: {discrepancies[discrepancy_key]}")

    # Merge discrepancies into combined_opportunity
    combined_opportunity.update(discrepancies)

    # Ensure all expected discrepancies are present
    expected_discrepancies = [
        'baseToken_difference_12', 'baseToken_difference_13', 'baseToken_difference_23',
        'quoteToken_difference_12', 'quoteToken_difference_13', 'quoteToken_difference_23'
    ]

    for key in expected_discrepancies:
        if key not in combined_opportunity:
            combined_opportunity[key] = '0.00%'  # or any default value you prefer
            print(f"Added missing discrepancy: {key}")

    # print("FINAL COMBINED_OPPORTUNITY~~~~~", combined_opportunity)

def safe_get(d, key, default=None):
    try:
        # If d is a dict or dict-like object
        if isinstance(d, dict):
            return d[key]
        # If d is an object with attributes
        else:
            return getattr(d, key, default)
    except (KeyError, AttributeError):
        return default




from typing import Dict, Union, List
def check_price_compatibility(opportunity: Dict[str, Union[str, float]], initial_investment: float, slippage: float, fee_percentage: float) -> bool:
    """
    Check if the third pair's price fits into the arbitrage chain to make a profit.
    
    :param opportunity: Dictionary containing details of the three pairs in the arbitrage opportunity
    :param initial_investment: The amount of USD to invest in the arbitrage
    :param slippage, slippage: Expected slippage for each trade
    :param fee_percentage: Trading fee percentage
    :return: Boolean indicating if the third pair's price would result in a profit
    """
    # Convert initial investment to the first token
    initial_amount = initial_investment / float(opportunity['pair1_price'])
    logging.debug(f"Initial amount after conversion: {initial_amount}")

    # Now simulate trades through all three pairs
    # This is a simplified model; real implementation would need to account for complex price dynamics
    amount_after_first_trade = initial_amount / (1 + slippage)
    logging.debug(f"Amount after first trade: {amount_after_first_trade}")
    price_first_to_second = float(opportunity['pair2_price'])
    amount_after_second_trade = (amount_after_first_trade * price_first_to_second) / (1 + slippage)
    logging.debug(f"Amount after second trade: {amount_after_second_trade}")
    price_second_to_third = float(opportunity['pair3_price'])
    final_amount = amount_after_second_trade / price_second_to_third
    logging.debug(f"Final amount after third trade: {final_amount}")

    # Fees calculation
    total_fees = initial_investment * fee_percentage * 3  # Assuming three trades, one for each pair
    logging.debug(f"Total fees for three trades: {total_fees}")

    # Profit calculation
    profit = (final_amount * float(opportunity['pair1_price'])) - initial_investment - total_fees
    logging.debug(f"Calculated profit: {profit}")

    return profit > 0

def get_user_purchases(user_id):
    """
    Fetch all purchases associated with a user ID from the database.
    """
    return Purchase.query.filter_by(user_id=user_id).all()

def gather_token_pairs_from_purchases(purchases, session):
    """
    Gather all token pairs from the user's purchase history with rate limiting.
    If there are no purchases, return an empty list to avoid unnecessary operations.
    """
    if not purchases:
        return []

    baseToken_addresses = [purchase.baseToken_address for purchase in purchases if purchase.baseToken_address]
    all_token_pairs = []
    for address in baseToken_addresses:
        if address not in seen_addresses:  # Assuming seen_addresses is global or passed somehow
            search = fetch_and_cache_pairs(session, address)
            if search:
                all_token_pairs.extend(process_token_pairs(search))
    return all_token_pairs

def find_arbitrage_opportunities_for_user(token_pairs, purchases, slippage, fee_percentage, initial_investment, search_address):
    """
    Find arbitrage opportunities based on either user's token pairs or a provided address.
    """
    if not token_pairs:  # If no user data, use the search_address
        search = fetch_and_cache_pairs(session, search_address)
        if search:
            token_pairs = process_token_pairs(search)
        else:
            logging.warning("No token pairs found for the given address.")
            return []

    return find_arbitrage_opportunities(token_pairs, slippage, fee_percentage, initial_investment, purchases)

def filter_and_process_opportunities(opportunities):
    """
    Filter opportunities to only include those where there are more than two unique addresses.
    """
    quote_pairs = []
    pair_chains = []

    for opportunity in opportunities:
        addresses = [
            opportunity['pair1_baseToken_address'],
            opportunity['pair1_quoteToken_address'],
            opportunity['pair2_baseToken_address'],
            opportunity['pair2_quoteToken_address']
        ]
        if opportunity['pair1_chain_id'] == opportunity['pair2_chain_id']:
            counter = Counter(addresses)
            repeated_item = next(item for item, count in counter.items() if count > 1)
            unique_items = tuple(item for item in addresses if item != repeated_item)
            quote_pairs.append(unique_items)
            pair_chains.append(opportunity['pair1_chain_id'])
    
    return quote_pairs, pair_chains

def match_pairs_with_opportunities(opportunities, quote_pairs, pair_chains):
    """
    Match the arbitrage opportunities with corresponding token pairs from the Dexscreener data.
    """
    seen_searches = defaultdict(bool)
    matching_pairs = []
    combined_data = list(zip(quote_pairs, pair_chains))

    for item in combined_data:
        address1, address2, chain_id = item[0][0], item[0][1], item[1]
        search_key = f"{chain_id}_{address1}"
        if not seen_searches[search_key]:
            seen_searches[search_key] = True
            search = client.get_token_pairs(address1)
            for pair in search:
                if pair.quote_token.address == address2 or pair.base_token.address == address2:
                    matching_pairs.append(pair)
                    break
            if item != combined_data[-1]:
                time.sleep(3)  # Delay to avoid rate limiting

    opportunities_with_pairs = []
    for opportunity in opportunities:
        new_opportunity = opportunity.copy()
        new_opportunity['matching_pairs'] = [pair for pair in matching_pairs if 
            pair.base_token.address in [opportunity['pair1_baseToken_address'], opportunity['pair1_quoteToken_address'], opportunity['pair2_baseToken_address'], opportunity['pair2_quoteToken_address']] or
            pair.quote_token.address in [opportunity['pair1_baseToken_address'], opportunity['pair1_quoteToken_address'], opportunity['pair2_baseToken_address'], opportunity['pair2_quoteToken_address']]
        ]
        opportunities_with_pairs.append(new_opportunity)

    return opportunities_with_pairs



def process_arbitrage_data(user_purchases, session, initial_investment, slippage, fee_percentage, search_address=None):
    """
    Process arbitrage data, using either user's purchase history or a provided search address.
    """
    token_pairs = gather_token_pairs_from_purchases(user_purchases, session)
    
    logging.info('Finding arbitrage opportunities')
    arbitrage_opportunities = find_arbitrage_opportunities_for_user(token_pairs, user_purchases, slippage, fee_percentage, initial_investment, search_address)
    # logging.info(f'Found {len(arbitrage_opportunities)} initial arbitrage opportunities.')

    # Continue with the rest of the function logic, ensuring to handle if opportunities are empty
    if not arbitrage_opportunities:
        logging.info('No arbitrage opportunities found.')
        return []

    quote_pairs, pair_chains = filter_and_process_opportunities(arbitrage_opportunities)
    opportunities_with_pairs = match_pairs_with_opportunities(arbitrage_opportunities, quote_pairs, pair_chains)

    unique_pair_addresses = sorted(set(p.pair_address for o in opportunities_with_pairs for p in o['matching_pairs']))

    logging.info('Finding third contract')
    all_three_contracts = find_third_contract_data(unique_pair_addresses, arbitrage_opportunities, session, initial_investment, slippage, fee_percentage)

    sorted_opportunities = sorted(all_three_contracts, key=lambda x: x['int_profit'], reverse=True)
    logging.info(f'Total arbitrage opportunities: {len(sorted_opportunities)}')

    return sorted_opportunities




# LOG LOADER
from logging import Filter, LogRecord 
from typing import List
# Custom handler to send logs to client
class HeartbeatFilter(Filter):
    def filter(self, record: LogRecord) -> bool:
        # Exclude debugger logs (all logs from Werkzeug)
        if record.name.startswith('werkzeug'):
            return False
        
        # Exclude records related to /get_logs, /landing_page_data, and /
        message = record.getMessage().lower()
        if '/get_logs' in message or '/landing_page_data' in message or 'get / ' in message:
            return False
        
        # Allow all other logs
        return True

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Create a custom handler for client logs
class ClientLoggingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs: List[str] = []
        # Add the heartbeat filter
        self.addFilter(HeartbeatFilter())

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        self.logs.append(log_entry)

    def get_logs(self) -> List[str]:
        logs = self.logs.copy()
        self.logs.clear()  # Clear after retrieval
        return logs

# Create and configure the logger
client_handler = ClientLoggingHandler()
logger.addHandler(client_handler)
