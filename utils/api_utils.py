import time
from dexscreener import DexscreenerClient

client = DexscreenerClient()

# Global variable for API rate limit
last_request_time = 0
request_delay = 7  # seconds

def rate_limit():
    global last_request_time
    current_time = time.time()
    if current_time - last_request_time < request_delay:
        time.sleep(request_delay - (current_time - last_request_time))
    last_request_time = time.time()

def fetch_current_price(asset_name):
    print('Fetching current price...')
    searchTicker = asset_name.lower()
    rate_limit()
    search = client.search_pairs(searchTicker)    
    for TokenPair in search:
        token_Pair = TokenPair.base_token.name + '/' + TokenPair.quote_token.name
        return {
            'price': float(TokenPair.price_usd),
              'source': 'Dexscreener', 
              'pairAddress': TokenPair.pair_address, 
              'name': TokenPair.base_token.name, 
              'pair_url': TokenPair.url, 
              'tokenPair': token_Pair,
              'baseToken_url': f'https://dexscreener.com/{TokenPair.chain_id}/{TokenPair.base_token.address}',
              'chain_id': TokenPair.chain_id
              }
