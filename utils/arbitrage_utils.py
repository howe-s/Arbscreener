def calculate_arbitrage_profit(initial_investment, price_pair1, price_pair2, slippage_pair1, slippage_pair2, fee_percentage):
    amount_pair1 = initial_investment / price_pair1
    adjusted_amount_pair1 = amount_pair1 * (1 - slippage_pair1)
    value_pair2 = adjusted_amount_pair1 * price_pair2
    final_amount_pair2 = value_pair2 * (1 - slippage_pair2)
    fees = initial_investment * fee_percentage * 2
    profit = final_amount_pair2 - initial_investment - fees
    return profit

def process_token_pairs(search):
    token_pairs = []
    for TokenPair in search:
        token_pairs.append({
            'pair': TokenPair.base_token.name + '/' + TokenPair.quote_token.name,
            'pool_address': TokenPair.pair_address,
            'pool_url': TokenPair.url,
            'price_usd': TokenPair.price_usd,
            'price_native': TokenPair.price_native,
            'liquidity_usd': TokenPair.liquidity.usd,
            'liquidity_base': TokenPair.liquidity.base,
            'liquidity_quote': TokenPair.liquidity.quote,
            'baseToken_address': TokenPair.base_token.address,
            'quoteToken_address': TokenPair.quote_token.address,
            'chain_id': TokenPair.chain_id,
            'dex_id': TokenPair.dex_id,
            'baseToken_name': TokenPair.base_token.name,
            'quoteToken_Name': TokenPair.quote_token.name
        })
    return token_pairs

def find_arbitrage_opportunities(token_pairs, slippage_pair1, slippage_pair2, fee_percentage, initial_investment, user_purchases):
    print('finding arb..')
    arbitrage_opportunities = []
    #loop through tokenPair list once
    for i, pair1 in enumerate(token_pairs):
        #loop through twice
        for pair2 in token_pairs[i + 1:]:
            # Check if baseAsset is same
            if (pair1['baseToken_address'] == pair2['baseToken_address']):
                #Check if price discrepency   
                if ((pair1['price_native'] < pair2['price_native'] or pair2['price_native'] < pair1['price_native']) and 
                    # Check if pools are the same
                    (pair1['liquidity_usd'] > pair2['liquidity_usd'] or pair2['liquidity_usd'] > pair1['liquidity_usd']) and 
                    pair1['liquidity_usd'] > 10000 and 
                    pair2['liquidity_usd'] > 10000):


                    liquidity_diff = pair1['liquidity_usd'] - pair2['liquidity_usd']
                    price_diff = pair2['price_native'] - pair1['price_native']
                    
                    profit = calculate_arbitrage_profit(initial_investment, 
                                                        pair1['price_native'], 
                                                        pair2['price_native'], 
                                                        slippage_pair1, 
                                                        slippage_pair2, 
                                                        fee_percentage)
                    print("profit", profit)
                    base_liquidity = min(pair1['liquidity_base'], pair2['liquidity_base'])
                    profit_sort_format = f"{profit:,.2f}"
                    int_profit = int(profit * 10**8) / 10**8
                    print("integer profit value", int_profit)
                    if int_profit > 0:
                        nativePrice_ratio = pair2['price_native']/ pair1['price_native']
                        nativePrice_ratio_round = f"{round(nativePrice_ratio, 4)}"
                        pair1_price_round = f"{round(pair1['price_usd'], 8)}"
                        pair2_price_round = f"{round(pair2['price_usd'], 8)}"
                        pair1_priceNative_round = f"{round(pair1['price_native'], 8)}"
                        pair2_priceNative_round = f"{round(pair2['price_native'], 8)}"
                        nativePrice_difference = pair2['price_native'] - pair1['price_native']
                        print(nativePrice_difference)

                                                # Calculate userArb_profit for each purchase and store it
                        user_arb_profits = []
                        for purchase in user_purchases:
                            if purchase.baseToken_address == pair1['baseToken_address']:
                                ### THIS MATH IS WRONG
                                userArb_profit = nativePrice_ratio * purchase.quantity 
                                print('userArb_profit', userArb_profit)
                                user_arb_profits.append({
                                    'purchase_id': purchase.id,
                                    'userArb_profit': f"{round(userArb_profit, 8)}",
                                    'asset_name': purchase.asset_name
                                })
                        

                        arbitrage_opportunities.append({
                            'pair1': pair1['pair'],
                            'pair1_price': pair1['price_usd'],
                            'pair1_price_round': pair1_price_round,
                            'pair1_liquidity': f"${pair1['liquidity_usd']:,.2f}",
                            'pair1_liquidity_base': f"{pair1['liquidity_base']:,.2f}",
                            'pair1_liquidity_quote': f"{pair1['liquidity_quote']:,.2f}",
                            'pool_pair1_address': pair1['pool_address'],
                            'pair1_baseToken_address': pair1['baseToken_address'],
                            'pair1_quoteToken_address': pair1['quoteToken_address'],
                            'pool_pair1_url': pair1['pool_url'],
                            'pair2': pair2['pair'],
                            'pair2_price': pair2['price_usd'],
                            'pair2_price_round': pair2_price_round,
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
                            'pair1_priceNative_round': pair1_priceNative_round,
                            'pair2_priceNative_round': pair2_priceNative_round,
                            'nativePrice_ratio': nativePrice_ratio,
                            'nativePrice_ratio_round': nativePrice_ratio_round,
                            'nativePrice_difference': nativePrice_difference,
                            'user_arb_profits': user_arb_profits
                        })
    return arbitrage_opportunities
