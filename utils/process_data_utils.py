def validate_data(data):
    if not data.get('tokenPairAddress'):
        return jsonify({"message": "Missing tokenPairAddress"}), 400
    return None

def process_search_results(search, token_pair_address, base_token):
    if isinstance(search, list):
        for pair in search:
            if pair.pair_address == token_pair_address:
                return prepare_detailed_response(pair, base_token)
        return None
    else:
        return prepare_simple_response(search)

def prepare_detailed_response(pair, base_token):
    transactions = {
        "m5": str(pair.transactions.m5),
        "h1": str(pair.transactions.h1),
        "h6": str(pair.transactions.h6),
        "h24": str(pair.transactions.h24)
    }

    x_data = ['5m', '1h', '6h', '24h']
    y_data = [pair.volume.m5, pair.volume.h1, pair.volume.h6, pair.volume.h24]

    chart_div = generate_bar_chart(x_data, y_data)  # Assuming this function is defined elsewhere

    return {
        'transactions': transactions,
        'chart_div': chart_div,
        'pair_URL': pair.url,
        'dex_id': pair.dex_id,
        'chain_id': pair.chain_id,
        'pair_address': pair.pair_address,
        'base_token': pair.base_token.name,
        'quote_token': pair.quote_token.name,
        'liquidity_usd': pair.liquidity.usd,
        'price_native': pair.price_native,
        'price_usd': pair.price_usd,
        'volume_24h': pair.volume.h24,
        'x_data': x_data,
        'y_data': y_data,
    }

def prepare_simple_response(search):
    try:
        return {
            "transactions": {
                "m5": str(search.transactions.m5),
                "h1": str(search.transactions.h1),
                "h6": str(search.transactions.h6),
                "h24": str(search.transactions.h24)
            }
        }
    except AttributeError:
        return None