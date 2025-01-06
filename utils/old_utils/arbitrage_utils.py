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
    def safe_get(obj, attr, default=None):
        """Helper function to safely access an attribute or return a default value."""
        try:
            return getattr(obj, attr, default) if obj is not None else default
        except AttributeError:
            return default

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

    return arbitrage_opportunities