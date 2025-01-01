from collections import Counter, defaultdict
from utils.arbitrage_utils import find_arbitrage_opportunities, process_token_pairs
from utils.models import Purchase
from dexscreener import DexscreenerClient
import time
from functools import wraps

client = DexscreenerClient()

def safe_get(obj, attr, default=None):
    """Helper function to safely access an attribute or return a default value."""
    try:
        return getattr(obj, attr, default) if obj is not None else default
    except AttributeError:
        return default

def rate_limited(max_per_second):
    """
    Decorator for rate limiting function calls.
    """
    min_interval = 1.0 / float(max_per_second)
    
    def decorator(func):
        last_time_called = [0.0]
        
        @wraps(func)
        def rate_limited_function(*args, **kargs):
            elapsed = time.time() - last_time_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kargs)
            last_time_called[0] = time.time()
            return ret
        return rate_limited_function
    return decorator

@rate_limited(1/3)  # 1 request per 3 seconds
def search_pairs_rate_limited(contract):
    """
    Search for pairs with rate limiting.
    """
    return client.search_pairs(contract)



def calculate_arbitrage_profit(initial_investment, price_pair1, price_pair2, slippage_pair1, slippage_pair2, fee_percentage, liquidity_pair1, liquidity_pair2):
    # Convert initial investment to amount in pair1
    amount_pair1 = initial_investment / price_pair1
    
    # Simplified slippage model
    def apply_slippage(amount, liquidity, slippage):
        return amount * (1 - slippage * (amount / liquidity))
    
    adjusted_amount_pair1 = apply_slippage(amount_pair1, liquidity_pair1, slippage_pair1)
    value_pair2 = adjusted_amount_pair1 * price_pair2
    final_amount_pair2 = apply_slippage(value_pair2, liquidity_pair2, slippage_pair2)
    
    # Calculate fees
    fees = initial_investment * fee_percentage * 2  # Now considering two trades
    
    # Profit calculation
    profit = final_amount_pair2 - initial_investment - fees
    
    return profit

def process_token_pairs(search):
    token_pairs = []
    for TokenPair in search:
        # print(TokenPair)
    
        
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

def find_arbitrage_opportunities(token_pairs, slippage_pair1, slippage_pair2, fee_percentage, initial_investment, user_purchases):
    print('finding arb..')
    arbitrage_opportunities = []
    for i, pair1 in enumerate(token_pairs):
        for j, pair2 in enumerate(token_pairs):
            if i != j:  # Ensure pairs are different
                # Check if pairs share a common token
                if pair1['baseToken_address'] == pair2['baseToken_address'] or pair1['quoteToken_address'] in [pair2['baseToken_address'], pair2['quoteToken_address']]:
                    # Check for price discrepancy and sufficient liquidity for the first two pairs
                    if (abs(pair2['price_native'] - pair1['price_native']) > 0 and 
                        pair1['liquidity_usd'] > 10000 and 
                        pair2['liquidity_usd'] > 10000):

                        liquidity_diff = pair1['liquidity_usd'] - pair2['liquidity_usd']
                        price_diff = pair2['price_native'] - pair1['price_native']
                        
                        base_liquidity = min(pair1['liquidity_base'], pair2['liquidity_base'])
                        profit = calculate_arbitrage_profit(initial_investment, 
                                                            pair1['price_native'], 
                                                            pair2['price_native'], 
                                                            slippage_pair1, 
                                                            slippage_pair2, 
                                                            fee_percentage,
                                                            pair1['liquidity_base'],
                                                            pair2['liquidity_base'])
                        
                        # print("profit with two pairs", profit)
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

    return arbitrage_opportunities # First two contracts

def find_third_contract_data(unique_pair_addresses, arbitrage_opportunities):
    third_pair_index = {}
    for contract in unique_pair_addresses:
        search = search_pairs_rate_limited(contract)
        if search:
            for pair in search:
                pair_details = {
                    'baseToken_address': safe_get(pair.base_token, 'address', 'N/A'),
                    'quoteToken_address': safe_get(pair.quote_token, 'address', 'N/A'),
                    'pair_address': safe_get(pair, 'pair_address', 'N/A'),
                    'pair': f"{safe_get(pair.base_token, 'name', 'N/A')}/{safe_get(pair.quote_token, 'name', 'N/A')}",
                    'price_usd': safe_get(pair, 'price_usd', 0.0),
                    'price_native': safe_get(pair, 'price_native', 0.0),
                    'liquidity': safe_get(pair, 'liquidity', {}),
                    'url': safe_get(pair, 'url', 'N/A'),
                    'chain_id': safe_get(pair, 'chain_id', 'N/A'),
                    'dex_id': safe_get(pair, 'dex_id', 'N/A')
                }
                third_pair_index[safe_get(pair, 'pair_address', 'N/A')] = pair_details

    combined_opportunities = []
    for opportunity in arbitrage_opportunities:
        matched_pair = None
        # Get non-repeating tokens from first and second pairs
        addresses = [
            opportunity['pair1_baseToken_address'],
            opportunity['pair1_quoteToken_address'],
            opportunity['pair2_baseToken_address'],
            opportunity['pair2_quoteToken_address']
        ]
        counter = Counter(addresses)
        unique_tokens = [addr for addr, count in counter.items() if count == 1]

        if len(unique_tokens) == 2:  # We have two unique tokens from the first and second pairs
            unique_token1, unique_token2 = unique_tokens
            for pair_address, pair_data in third_pair_index.items():
                if (pair_data['baseToken_address'] == unique_token1 and pair_data['quoteToken_address'] == unique_token2) or \
                   (pair_data['baseToken_address'] == unique_token2 and pair_data['quoteToken_address'] == unique_token1):
                    matched_pair = pair_data
                    break

        if matched_pair:  # Only proceed if a third matching pair was found
            combined_opportunity = opportunity.copy()
            combined_opportunity.update({
                'pair3': matched_pair['pair'],
                'pair3_price': matched_pair['price_usd'],
                'pair3_price_round': f"{round(matched_pair['price_usd'], 8)}",
                'pair3_liquidity': f"${safe_get(matched_pair['liquidity'], 'usd', 0.0):,.2f}",
                'pair3_liquidity_base': f"{safe_get(matched_pair['liquidity'], 'base', 0.0):,.2f}",
                'pair3_liquidity_quote': f"{safe_get(matched_pair['liquidity'], 'quote', 0.0):,.2f}",
                'pool_pair3_address': matched_pair['pair_address'],
                'pair3_baseToken_address': matched_pair['baseToken_address'],
                'pair3_quoteToken_address': matched_pair['quoteToken_address'],
                'pool_pair3_url': matched_pair['url'],
                'pair3_chain_id': matched_pair['chain_id'],
                'pair3_dex_id': matched_pair['dex_id'],
                'pair3_priceNative': matched_pair['price_native'],
                'pair3_priceNative_round': f"{round(matched_pair['price_native'], 8)}"
            })
            combined_opportunities.append(combined_opportunity)

    return combined_opportunities

    # Here we integrate the matching logic directly

    # Create an index for quick lookup from third_pair
    # third_pair_index = {pair['baseToken_address']: pair for pair in third_pair}
    # third_pair_index.update({pair['quoteToken_address']: pair for pair in third_pair})

    # combined_opportunities = []

    # for opportunity in arbitrage_opportunities:
    #     matched_pair = None

    #     # Check each address against the third_pair index
    #     addresses_to_check = [
    #         opportunity['pair1_baseToken_address'],
    #         opportunity['pair1_quoteToken_address'],
    #         opportunity['pair2_baseToken_address'],
    #         opportunity['pair2_quoteToken_address']
    #     ]

    #     for address in addresses_to_check:
    #         if address in third_pair_index:
    #             matched_pair = third_pair_index[address]
    #             break  # Assuming you want to match only one third pair per opportunity

    #     # Create a new combined opportunity object
    #     combined_opportunity = opportunity.copy()

    #     if matched_pair:
    #         combined_opportunity.update({
    #             'pair3': matched_pair['pair'],
    #             'pair3_price': matched_pair['price_usd'],
    #             'pair3_price_round': f"{round(matched_pair['price_usd'], 8)}",
    #             'pair3_liquidity': f"${matched_pair['liquidity_usd']:,.2f}",
    #             'pair3_liquidity_base': f"{matched_pair['liquidity_base']:,.2f}",
    #             'pair3_liquidity_quote': f"{matched_pair['liquidity_quote']:,.2f}",
    #             'pool_pair3_address': matched_pair['pool_address'],
    #             'pair3_baseToken_address': matched_pair['baseToken_address'],
    #             'pair3_quoteToken_address': matched_pair['quoteToken_address'],
    #             'pool_pair3_url': matched_pair['pool_url'],
    #             'pair3_chain_id': matched_pair['chain_id'],
    #             'pair3_dex_id': matched_pair['dex_id'],
    #             'pair3_priceNative': matched_pair['price_native'],
    #             'pair3_priceNative_round': f"{round(matched_pair['price_native'], 8)}"
    #         })

    #     combined_opportunities.append(combined_opportunity)
    
    # print('~~~~~~~~~~~~COMBINED OPPORTUNITIES~~~~~~~~')
    # print(combined_opportunities)
    # return combined_opportunities

def get_user_purchases(user_id):
    """
    Fetch all purchases associated with a user ID from the database.
    """
    return Purchase.query.filter_by(user_id=user_id).all()

def gather_token_pairs_from_purchases(purchases):
    """
    Gather all token pairs from the user's purchase history with rate limiting.
    """
    baseToken_addresses = [purchase.baseToken_address for purchase in purchases]
    all_token_pairs = []
    for address in baseToken_addresses:
        search = search_pairs_rate_limited(address)
        if search:
            all_token_pairs.extend(process_token_pairs(search))
    return all_token_pairs

def find_arbitrage_opportunities_for_user(token_pairs, purchases, slippage_pair1, slippage_pair2, fee_percentage, initial_investment):
    """
    Find arbitrage opportunities based on user's token pairs.
    """
    return find_arbitrage_opportunities(token_pairs, slippage_pair1, slippage_pair2, fee_percentage, initial_investment, purchases)

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