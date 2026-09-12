from collections import Counter, defaultdict, deque
import math
from dexscreener import TokenPair
from pydantic import ValidationError
from threading import Lock
import time
from functools import wraps
from typing import Union, List, Dict
import random
import requests

rate_lock = Lock()

api_call_counter = Counter()

requests_this_minute = 0
last_reset_time = 0


def safe_get(obj, attr, default=None):
    """Helper function to safely access an attribute or return a default value."""
    try:
        value = obj.get(attr, default) if isinstance(obj, dict) else getattr(obj, attr, default)
        return default if value is None else value
    except AttributeError:
        return default


def retry_with_backoff(func, max_retries=3, initial_delay=1, backoff_factor=2):
    """
    Decorator to retry API calls with exponential backoff in case of rate limiting.
    """
    @wraps(func)
    def wrapper(*args, **kargs):
        retries = 0
        while retries < max_retries:
            try:
                return func(*args, **kargs)
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    delay = initial_delay * (backoff_factor ** retries) + random.uniform(0, 1)
                    time.sleep(delay)
                    retries += 1
                    if retries == max_retries:
                        raise
                else:
                    raise
        return None  # or handle as appropriate if all retries fail
    return wrapper


def rate_limited(max_calls_per_minute):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global requests_this_minute, last_reset_time
            while True:
                with rate_lock:
                    now = time.monotonic()
                    if now - last_reset_time >= 60:
                        requests_this_minute, last_reset_time = 0, now
                    if requests_this_minute < max_calls_per_minute:
                        requests_this_minute += 1
                        break
                    delay = max(0, 60 - (now - last_reset_time))
                time.sleep(delay)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@retry_with_backoff
@rate_limited(60)  # Adjust rate limiting as needed
def fetch_and_cache_pairs(contract: Union[str, List[str]]):
    """
    Fetch pairs with rate limiting, caching, and address checking.
    """
    if isinstance(contract, list):
        search_query = ", ".join(contract)
    else:
        search_query = contract

    response = requests.get('https://api.dexscreener.com/latest/dex/search',
                            params={'q': search_query}, timeout=(5, 15))
    response.raise_for_status()
    pairs = []
    for raw in response.json().get('pairs') or []:
        try:
            pairs.append(TokenPair(**raw))
        except (TypeError, ValidationError):
            logger.warning('Skipping malformed market data')
    return pairs

def finite_number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else 0.0
    except (TypeError, ValueError):
        return 0.0


def process_token_pairs(dex_pairs):
    formatted_pairs = []
    for pair in dex_pairs or []:
        liquidity_data = safe_get(pair, 'liquidity', {})

        formatted_pairs.append({
            'pair': safe_get(pair.base_token, 'name', 'N/A') + '/' + safe_get(pair.quote_token, 'name', 'N/A'),
            'pool_address': safe_get(pair, 'pair_address', 'N/A'),
            'pool_url': safe_get(pair, 'url', 'N/A'),
            'price_usd': finite_number(safe_get(pair, 'price_usd', 0.0)),
            'price_native': finite_number(safe_get(pair, 'price_native', 0.0)),
            'liquidity_usd': finite_number(safe_get(liquidity_data, 'usd', 0.0)),
            'liquidity_base': finite_number(safe_get(liquidity_data, 'base', 0.0)),
            'liquidity_quote': finite_number(safe_get(liquidity_data, 'quote', 0.0)),
            'baseToken_address': safe_get(pair.base_token, 'address', 'N/A'),
            'quoteToken_address': safe_get(pair.quote_token, 'address', 'N/A'),
            'chain_id': safe_get(pair, 'chain_id', 'N/A'),
            'dex_id': safe_get(pair, 'dex_id', 'N/A'),
            'baseToken_name': safe_get(pair.base_token, 'name', 'N/A'),
            'quoteToken_name': safe_get(pair.quote_token, 'name', 'N/A')
        })
    return formatted_pairs

def calculate_arbitrage_profit(
    investment_amount,
    entry_price,
    exit_price,
    slippage_rate,
    fee_rate,
    entry_liquidity,
    exit_liquidity
):
    if min(investment_amount, entry_price, exit_price, entry_liquidity, exit_liquidity) <= 0:
        raise ValueError('Investment, prices and liquidity must be positive')
    entry_value = investment_amount * max(0, 1 - slippage_rate * investment_amount / entry_liquidity)
    exit_value = entry_value / entry_price * exit_price
    final_amount = exit_value * max(0, 1 - slippage_rate * exit_value / exit_liquidity)
    profit = final_amount - investment_amount - investment_amount * fee_rate * 2
    return profit if math.isfinite(profit) else -investment_amount


import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_arbitrage_opportunities(token_pairs, slippage, fee_percentage, initial_investment, user_purchases, include_unprofitable=False):
    """Build same-chain routes; different quote currencies require a closing pool."""
    logger.info('Finding same-chain arbitrage routes')
    opportunities = []
    valid = [p for p in token_pairs if all(finite_number(p.get(k)) > 0 for k in
             ('price_usd', 'price_native', 'liquidity_base', 'liquidity_quote'))
             and finite_number(p.get('liquidity_usd')) > 10000]
    for p in valid:
        for q in valid:
            if p['chain_id'] != q['chain_id'] or p['pool_address'] == q['pool_address']:
                continue
            tokens1 = {p['baseToken_address'], p['quoteToken_address']}
            tokens2 = {q['baseToken_address'], q['quoteToken_address']}
            shared = tokens1 & tokens2
            if not shared:
                continue
            common = p['baseToken_address'] if p['baseToken_address'] in shared else p['quoteToken_address']
            def usd(pair):
                return pair['price_usd'] if pair['baseToken_address'] == common else pair['price_usd'] / pair['price_native']
            entry, exit_price = usd(p), usd(q)
            triangular = len(tokens1 | tokens2) == 3
            if not triangular:
                entry_rate = p['price_native'] if p['baseToken_address'] == common else 1 / p['price_native']
                exit_rate = q['price_native'] if q['baseToken_address'] == common else 1 / q['price_native']
                exit_price = entry * exit_rate / entry_rate
            profit = calculate_arbitrage_profit(initial_investment, entry, exit_price, slippage,
                                                fee_percentage, p['liquidity_usd'], q['liquidity_usd'])
            if not triangular and profit <= 0 and not include_unprofitable:
                continue
            opportunity = {'int_profit': profit, 'profit': f'${profit:,.2f}',
                           'price_diff': f'${exit_price - entry:,.2f}',
                           'economics': {'investment': initial_investment,
                               'revenue': initial_investment + profit + initial_investment * fee_percentage * 2,
                               'fees': initial_investment * fee_percentage * 2}}
            for n, pair in enumerate((p, q), 1):
                for key in ('baseToken_address', 'quoteToken_address', 'chain_id', 'dex_id'):
                    opportunity[f'pair{n}_{key}'] = pair[key]
                opportunity.update({f'pair{n}': pair['pair'], f'pair{n}_price': pair['price_usd'],
                    f'pair{n}_price_round': str(pair['price_usd']),
                    f'pair{n}_priceNative': pair['price_native'],
                    f'pair{n}_priceNative_round': str(pair['price_native']),
                    f'pool_pair{n}_address': pair['pool_address'], f'pool_pair{n}_url': pair['pool_url'],
                    f'pair{n}_liquidity': f"${pair['liquidity_usd']:,.2f}",
                    f'pair{n}_liquidity_base': f"{pair['liquidity_base']:,.2f}",
                    f'pair{n}_liquidity_quote': f"{pair['liquidity_quote']:,.2f}",
                    f'quote_price_usd_{n}': f"${pair['price_usd'] / pair['price_native']:.8g}"})
            opportunities.append(opportunity)
    return opportunities


def find_third_contract_data(unique_pair_addresses, arbitrage_opportunities, initial_investment, slippage, fee_percentage, third_pair_index=None, include_unprofitable=False):
    logger.info('Finding third contract data')
    combined_opportunities = []
    best_routes = {}

    # Fetch or use cached data for third pair
    if third_pair_index is None:
        third_pair_index = fetch_or_use_cached_data(unique_pair_addresses)

    logger.info(f'Indexed {len(third_pair_index)} third contracts')

    for opportunity in arbitrage_opportunities:
        for address, pair in third_pair_index.items():
            matched_pair = find_matching_third_pair(opportunity, {address: pair})
            if not matched_pair:
                continue
            combined = combine_opportunity_data(opportunity, matched_pair)
            key = (combined['pair1_chain_id'],) + tuple(sorted(
                combined[f'pool_pair{n}_address'] for n in (1, 2, 3)))
            if check_price_compatibility(combined, initial_investment, slippage, fee_percentage, include_unprofitable):
                calculate_usd_prices(combined)
                calculate_price_discrepancies(combined)
                if key not in best_routes or combined['int_profit'] > best_routes[key]['int_profit']:
                    best_routes[key] = combined
    combined_opportunities = list(best_routes.values())

    logger.info(f'Final number of arbitrage opportunities with third pair: {len(combined_opportunities)}')
    return combined_opportunities

def fetch_or_use_cached_data(unique_pair_addresses):
    third_pair_index = {}
    should_fetch_new_data = check_for_price_change(unique_pair_addresses)

    if should_fetch_new_data:
        for contract in unique_pair_addresses:
            search = fetch_and_cache_pairs(contract)
            if search:
                for pair in search:
                    liquidity_data = safe_get(pair, 'liquidity', {})
                    if (finite_number(safe_get(liquidity_data, 'usd')) > 10000
                            and finite_number(safe_get(pair, 'price_usd')) > 0
                            and finite_number(safe_get(pair, 'price_native')) > 0):
                        pair_details = create_pair_details(pair)
                        third_pair_index[(pair_details['chain_id'], pair_details['pair_address'])] = pair_details
                        # Removed database update
                        logger.debug(f"Added to third_pair_index: {pair_details}")
            else:
                logger.debug(f'No search results for contract {contract}')
    else:
        for contract in unique_pair_addresses:
            # Removed database retrieval
            logger.warning(f'No stored data for contract address: {contract}')

    return third_pair_index

def check_for_price_change(unique_pair_addresses):
    for contract in unique_pair_addresses:
        last_known_price = get_last_known_price(contract)
        if last_known_price is None:
            return True
        search = fetch_and_cache_pairs(contract)
        if search and any(float(finite_number(safe_get(pair, 'price_native', 0.0))) != last_known_price for pair in search if safe_get(pair, 'pair_address') == contract):
            return True
    return False

def get_last_known_price(contract_address):
    # Removed database retrieval
    logger.debug(f"No stored data for contract address: {contract_address}")
    return None

def create_pair_details(pair):
    liquidity_data = safe_get(pair, 'liquidity', {})
    return {
        'baseToken_address': safe_get(pair.base_token, 'address', 'N/A'),
        'quoteToken_address': safe_get(pair.quote_token, 'address', 'N/A'),
        'pair_address': safe_get(pair, 'pair_address', 'N/A'),
        'pair': f"{safe_get(pair.base_token, 'name', 'N/A')}/{safe_get(pair.quote_token, 'name', 'N/A')}",
        'price_usd': float(finite_number(safe_get(pair, 'price_usd', 0.0))),
        'price_native': float(finite_number(safe_get(pair, 'price_native', 0.0))),
        'liquidity': liquidity_data,
        'url': safe_get(pair, 'url', 'N/A'),
        'chain_id': safe_get(pair, 'chain_id', 'N/A'),
        'dex_id': safe_get(pair, 'dex_id', 'N/A')
    }

def find_matching_third_pair(opportunity, third_pair_index):
    third_pair_index = {key: pair for key, pair in third_pair_index.items()
                        if pair['chain_id'] == opportunity['pair1_chain_id']
                        and pair['pair_address'] not in (opportunity['pool_pair1_address'], opportunity['pool_pair2_address'])}
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
        'pair3_priceNative': matched_pair['price_native'],
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
    quote_price_usd_1 = float(combined_opportunity['pair1_price']) / float(combined_opportunity.get('pair1_priceNative', combined_opportunity['pair1_priceNative_round']))
    quote_price_usd_2 = 1.0 if combined_opportunity['pair2_quoteToken_address'].lower() == 'usd' else float(combined_opportunity['pair2_price']) / float(combined_opportunity.get('pair2_priceNative', combined_opportunity['pair2_priceNative_round']))
    quote_price_usd_3 = 1.0 if combined_opportunity['pair3_quoteToken_address'].lower() == 'usd' else float(combined_opportunity['pair3_price']) / float(combined_opportunity.get('pair3_priceNative', combined_opportunity['pair3_priceNative_round']))

    combined_opportunity['quote_price_usd_1'] = f"${quote_price_usd_1:.8g}"
    combined_opportunity['quote_price_usd_2'] = f"${quote_price_usd_2:.8g}"
    combined_opportunity['quote_price_usd_3'] = f"${quote_price_usd_3:.8g}"

def calculate_price_discrepancies(combined_opportunity):

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


def check_price_compatibility(opportunity: Dict[str, Union[str, float]], initial_investment: float, slippage: float, fee_percentage: float, include_unprofitable=False) -> bool:
    """
    Check if the third pair's price fits into the arbitrage chain to make a profit.

    :param opportunity: Dictionary containing details of the three pairs in the arbitrage opportunity
    :param initial_investment: The amount of USD to invest in the arbitrage
    :param slippage, slippage: Expected slippage for each trade
    :param fee_percentage: Trading fee percentage
    :return: Boolean indicating if the third pair's price would result in a profit
    """
    # Start in the token unique to pool 1, traverse 1 -> 2 -> 3, and close the cycle.
    first = {opportunity['pair1_baseToken_address'], opportunity['pair1_quoteToken_address']}
    second = {opportunity['pair2_baseToken_address'], opportunity['pair2_quoteToken_address']}
    starts = first - second
    if len(starts) != 1:
        return False
    start = token = starts.pop()
    price = float(opportunity['pair1_price'])
    if start == opportunity['pair1_quoteToken_address']:
        price /= float(opportunity['pair1_priceNative'])
    amount = initial_investment / price
    gross_amount = amount
    for n in (1, 2, 3):
        base, quote = opportunity[f'pair{n}_baseToken_address'], opportunity[f'pair{n}_quoteToken_address']
        rate = float(opportunity[f'pair{n}_priceNative'])
        if rate <= 0:
            return False
        if token == base:
            amount *= rate
            gross_amount *= rate
            token = quote
        elif token == quote:
            amount /= rate
            gross_amount /= rate
            token = base
        else:
            return False
        amount *= (1 - slippage) * (1 - fee_percentage)
        gross_amount *= 1 - slippage
    profit = amount * price - initial_investment
    if token != start or not math.isfinite(profit) or (profit <= 0 and not include_unprofitable):
        return False
    opportunity.update(int_profit=profit, profit=f'${profit:,.2f}',
        economics={'investment': initial_investment, 'revenue': gross_amount * price,
                   'fees': max(0, (gross_amount - amount) * price)})
    return True


def get_user_purchases(user_id):
    """
    Fetch all purchases associated with a user ID from the database.
    """
    return []  # Removed database query

def gather_token_pairs_from_purchases(purchases):
    """
    Gather all token pairs from the user's purchase history with rate limiting.
    If there are no purchases, return an empty list to avoid unnecessary operations.
    """
    if not purchases:
        return []

    baseToken_addresses = [purchase.baseToken_address for purchase in purchases if purchase.baseToken_address]
    all_token_pairs = []
    for address in baseToken_addresses:
        search = fetch_and_cache_pairs(address)
        if search:
            all_token_pairs.extend(process_token_pairs(search))
    return all_token_pairs

def find_arbitrage_opportunities_for_user(token_pairs, purchases, slippage, fee_percentage, initial_investment, search_address, include_unprofitable=False):
    """
    Find arbitrage opportunities based on either user's token pairs or a provided address.
    """
    if not token_pairs:  # If no user data, use the search_address
        search = fetch_and_cache_pairs(search_address)
        if search:
            token_pairs = process_token_pairs(search)
        else:
            logger.warning("No token pairs found for the given address.")
            return []

    return find_arbitrage_opportunities(token_pairs, slippage, fee_percentage, initial_investment, purchases, include_unprofitable)

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
            if len(counter) != 3:
                continue
            repeated_item = next(item for item, count in counter.items() if count > 1)
            unique_items = tuple(item for item in addresses if item != repeated_item)
            quote_pairs.append(unique_items)
            pair_chains.append(opportunity['pair1_chain_id'])

    return quote_pairs, pair_chains

def match_pairs_with_opportunities(opportunities, quote_pairs, pair_chains):
    """
    Match the arbitrage opportunities with corresponding token pairs from the Dexscreener data.
    """
    seen_searches = {}
    matching_pairs = []
    combined_data = list(zip(quote_pairs, pair_chains))

    for item in combined_data:
        address1, address2, chain_id = item[0][0], item[0][1], item[1]
        search_key = f"{chain_id}_{address1}"
        if search_key not in seen_searches:
            seen_searches[search_key] = fetch_and_cache_pairs(address1)
        for pair in seen_searches[search_key] or []:
            if pair.chain_id == chain_id and {pair.quote_token.address, pair.base_token.address} == {address1, address2}:
                matching_pairs.append(pair)

    opportunities_with_pairs = []
    for opportunity in opportunities:
        new_opportunity = opportunity.copy()
        new_opportunity['matching_pairs'] = [pair for pair in matching_pairs if
            pair.base_token.address in [opportunity['pair1_baseToken_address'], opportunity['pair1_quoteToken_address'], opportunity['pair2_baseToken_address'], opportunity['pair2_quoteToken_address']] or
            pair.quote_token.address in [opportunity['pair1_baseToken_address'], opportunity['pair1_quoteToken_address'], opportunity['pair2_baseToken_address'], opportunity['pair2_quoteToken_address']]
        ]
        opportunities_with_pairs.append(new_opportunity)

    return opportunities_with_pairs


def process_arbitrage_data(user_purchases, initial_investment, slippage, fee_percentage, search_address=None, include_unprofitable=False):
    logger.info('Processing arbitrage data')
    token_pairs = gather_token_pairs_from_purchases(user_purchases)

    logger.info('Finding arbitrage opportunities')
    arbitrage_opportunities = find_arbitrage_opportunities_for_user(token_pairs, user_purchases, slippage, fee_percentage, initial_investment, search_address, include_unprofitable)
    logger.info(f'Found {len(arbitrage_opportunities)} initial arbitrage opportunities.')

    # Continue with the rest of the function logic, ensuring to handle if opportunities are empty
    if not arbitrage_opportunities:
        logger.info('No arbitrage opportunities found.')
        return []

    quote_pairs, pair_chains = filter_and_process_opportunities(arbitrage_opportunities)
    opportunities_with_pairs = match_pairs_with_opportunities(arbitrage_opportunities, quote_pairs, pair_chains)

    # Reuse the closing pools already fetched: avoid another request for every pool.
    third_pair_index = {}
    for opportunity in opportunities_with_pairs:
        for pair in opportunity['matching_pairs']:
            if (finite_number(safe_get(safe_get(pair, 'liquidity'), 'usd')) > 10000
                    and finite_number(safe_get(pair, 'price_usd')) > 0
                    and finite_number(safe_get(pair, 'price_native')) > 0):
                details = create_pair_details(pair)
                third_pair_index[(details['chain_id'], details['pair_address'])] = details
    all_three_contracts = find_third_contract_data(
        [], arbitrage_opportunities, initial_investment, slippage, fee_percentage,
        third_pair_index=third_pair_index, include_unprofitable=include_unprofitable)

    direct = [o for o in arbitrage_opportunities if
              {o['pair1_baseToken_address'], o['pair1_quoteToken_address']} ==
              {o['pair2_baseToken_address'], o['pair2_quoteToken_address']}]
    sorted_opportunities = sorted(direct + all_three_contracts, key=lambda x: x['int_profit'], reverse=True)
    logger.info(f'Total arbitrage opportunities: {len(sorted_opportunities)}')

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
        self.logs = deque(maxlen=500)
        # Add the heartbeat filter
        self.addFilter(HeartbeatFilter())

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        self.logs.append(log_entry)

    def get_logs(self) -> List[str]:
        self.acquire()
        try:
            logs = list(self.logs)
            self.logs.clear()
            return logs
        finally:
            self.release()

# Create and configure the logger
client_handler = ClientLoggingHandler()
logger.addHandler(client_handler)
