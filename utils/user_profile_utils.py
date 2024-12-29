from collections import Counter, defaultdict
from utils.arbitrage_utils import find_arbitrage_opportunities, process_token_pairs
from utils.models import Purchase
from dexscreener import DexscreenerClient
import time

client = DexscreenerClient()  # Assuming this is how you initialize the DexscreenerClient

def get_user_purchases(user_id):
    """
    Fetch all purchases associated with a user ID from the database.
    """
    return Purchase.query.filter_by(user_id=user_id).all()

def gather_token_pairs_from_purchases(purchases):
    """
    Gather all token pairs from the user's purchase history.
    """
    baseToken_addresses = [purchase.baseToken_address for purchase in purchases]
    all_token_pairs = []
    for address in baseToken_addresses:
        search = client.search_pairs(address)
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