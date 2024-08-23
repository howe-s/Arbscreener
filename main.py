import subprocess
import sys

# Function to install packages
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# List of required packages
required_packages = [
    'Flask',
    'matplotlib',
    'numpy==1.26.4',
    'pandas',
    'squarify',
    'dexscreener',
    'plotly',
    'flask_cors', 
    'requests',
    'jinja2'
]

# Check and install each package
for package in required_packages:
    try:
        __import__(package.split('==')[0])
    except ImportError:
        install(package)

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from dexscreener import DexscreenerClient
import matplotlib

matplotlib.use('Agg')  # Use non-interactive backend for server-side plotting
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
import squarify
import pandas as pd
from flask_cors import CORS
import requests

app = Flask(__name__)
client = DexscreenerClient()


def get_price_change_style(price_change):
    if price_change > 0:
        return "color: green;"
    elif price_change < 0:
        return "color: red;"
    else:
        return "color: gray;"


def format_price_change(price_change):
    return f"{price_change:.2f}%"


def combine_others(data, threshold=0.05):
    total = sum(value for _, value in data)
    result = []
    other_sum = 0
    for label, value in data:
        if value / total >= threshold:
            result.append((label, value))
        else:
            other_sum += value
    if other_sum > 0:
        result.append(("Others", other_sum))
    return result


def tree_chart_liquidity(data):
    data = combine_others(data)
    labels = [f"{label}\n${value:,.0f}" for label, value in data]
    sizes = [value for _, value in data]

    plt.figure(figsize=(8, 6))
    squarify.plot(sizes=sizes, label=labels, alpha=0.8)
    plt.axis('off')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return img


def pie_chart_liquidity(data):
    data = combine_others(data)
    labels = [f"{label} (${value:,.0f})" for label, value in data]
    sizes = [value for _, value in data]

    plt.figure(figsize=(8, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return img


def tree_chart_volume(data):
    data = combine_others(data)
    labels = [f"{label}\n${value:,.0f}" for label, value in data]
    sizes = [value for _, value in data]

    plt.figure(figsize=(8, 6))
    squarify.plot(sizes=sizes, label=labels, alpha=0.8)
    plt.axis('off')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return img


def pie_chart_volume(data):
    data = combine_others(data)
    labels = [f"{label} (${value:,.0f})" for label, value in data]
    sizes = [value for _, value in data]

    plt.figure(figsize=(8, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return img

from jinja2 import Environment
from markupsafe import Markup
from html import escape

def format_number(value, decimals=0, thousands_sep=',', decimal_sep='.'):
    """Formats a number with the specified decimal places, thousands separator, and decimal separator.

    Args:
        value (float or int): The number to be formatted.
        decimals (int, optional): The number of decimal places to display. Defaults to 0.
        thousands_sep (str, optional): The character to use as the thousands separator. Defaults to ','.
        decimal_sep (str, optional): The character to use as the decimal separator. Defaults to '.'.

    Returns:
        str: The formatted number.
    """

    formatted_value = f"{value:,.{decimals}f}"
    return Markup(escape(formatted_value))  # Use Markup for safe HTML output




@app.route('/', methods=['GET', 'POST'])
def index():
    # Get the user input for ticker and perform the search
    searchTicker = request.args.get('user_input', 'SOL').lower()    
    search = client.search_pairs(searchTicker)
    pool_data = []
    for TokenPair in search:
        print(TokenPair.liquidity)
        pool_data.append({
            'chain_id': TokenPair.chain_id,
            'liquidity': TokenPair.liquidity,
            'liquidity_usd_formatted': f"${TokenPair.liquidity.usd:,.2f}",
            'liquidity_base_formatted': f"{TokenPair.liquidity.base:,.2f}",
            'liquidity_quote_formatted': f"{TokenPair.liquidity.quote:,.2f}",            
            'price_native': TokenPair.price_native,
            'price_usd': TokenPair.price_usd,
            'price_usd_formatted': f"${TokenPair.price_usd:,.2f}",
            'volume_5m': TokenPair.volume.m5,  # Store the raw numerical value
            'volume_5m_formatted': f"${TokenPair.volume.m5:,.2f}",  # Formatted string for display
            'volume_1h': TokenPair.volume.h1,  # Store the raw numerical value
            'volume_1h_formatted': f"${TokenPair.volume.h1:,.2f}",  # Formatted string for display
            'volume_6h': TokenPair.volume.h6,  # Store the raw numerical value
            'volume_6h_formatted': f"${TokenPair.volume.h6:,.2f}",  # Formatted string for display
            'volume_24h': TokenPair.volume.h24,  # Store the raw numerical value
            'volume_24h_formatted': f"${TokenPair.volume.h24:,.2f}",  # Formatted string for display
            'pool_address': TokenPair.pair_address,
            'quote_token': TokenPair.quote_token.symbol,
            'base_token': TokenPair.base_token.symbol
        })

    sorted_pool = sorted(pool_data, key=lambda x: x['volume_24h'], reverse=True)
    # Pass the data to the template
    return render_template('index.html', pool_data=sorted_pool, user_input=searchTicker)


@app.route('/arb', methods=['GET', 'POST'])
def arb():
    # Get the user input for ticker and perform the search
    searchTicker = request.args.get('user_input', 'SOL').lower()
    search = client.search_pairs(searchTicker)
    
    # Extract data for processing
    token_pairs = []
    for TokenPair in search:
        token_pairs.append({
            'pair': TokenPair.quote_token.name + '/' + TokenPair.base_token.name,
            'pool_address': TokenPair.pair_address,
            'pool_url': TokenPair.url,
            'price_usd': TokenPair.price_usd,
            'liquidity_usd': TokenPair.liquidity.usd,
            'liquidity_base': TokenPair.liquidity.base,
            'liquidity_quote': TokenPair.liquidity.quote
        })
    
    # Initialize a list to store arbitrage opportunities
    arbitrage_opportunities = []
    
    # Compare each TokenPair with others to find arbitrage opportunities
    for i, pair1 in enumerate(token_pairs):
        for pair2 in token_pairs[i + 1:]:
            
            # Arbitrage opportunity condition
            if (pair1['price_usd'] < pair2['price_usd'] and 
                pair1['liquidity_usd'] > pair2['liquidity_usd']):

                liquidity_diff = pair1['liquidity_usd'] - pair2['liquidity_usd']
                price_diff = pair2['price_usd'] - pair1['price_usd']
                profit = liquidity_diff * price_diff
                
                # Determine base liquidity and potential profit
                if pair1['price_usd'] < pair2['price_usd']:
                    base_liquidity = pair1['liquidity_base']
                else:
                    base_liquidity = pair2['liquidity_base']

                potential_profit = base_liquidity * price_diff
                
                arbitrage_opportunities.append({
                    'pair1': pair1['pair'],
                    'pair1_price': f"${pair1['price_usd']:,.2f}",
                    'pair1_liquidity': f"${pair1['liquidity_usd']:,.2f}",
                    'pair1_liquidity_base': f"{pair1['liquidity_base']:,.2f}",
                    'pair1_liquidity_quote': f"{pair1['liquidity_quote']:,.2f}",
                    'pool_pair1_address': pair1['pool_address'],
                    'pool_pair1_url': pair1['pool_url'],
                    'pair2': pair2['pair'],
                    'pair2_price': f"${pair2['price_usd']:,.2f}",
                    'pair2_liquidity': f"${pair2['liquidity_usd']:,.2f}",
                    'pair2_liquidity_base': f"{pair2['liquidity_base']:,.2f}",
                    'pair2_liquidity_quote': f"{pair2['liquidity_quote']:,.2f}",
                    'pool_pair2_address': pair2['pool_address'],  
                    'pool_pair2_url': pair2['pool_url'],
                    'price_diff': f"${price_diff:,.2f}",
                    'liquidity_diff': f"${liquidity_diff:,.2f}",
                    'profit': f"${profit:,.2f}",
                    'potential_profit': f"${potential_profit:,.2f}"  # Add the potential profit
                })

    # Sort arbitrage opportunities by price_diff (big -> small)
    sorted_opportunities = sorted(arbitrage_opportunities, key=lambda x: x['price_diff'], reverse=True)

    print(arbitrage_opportunities)
    
    # Pass the data to the template
    return render_template('arb.html', search=search, user_input=searchTicker, arbitrage_opportunities=sorted_opportunities)




@app.route('/trending', methods=['GET', 'POST'])
def trending():
    #Passing the initial data
    searchTicker = request.args.get('user_input', 'SOL').lower()
    search = client.search_pairs(searchTicker)
    
    return render_template('trending.html', search=search, user_input=searchTicker)

@app.route('/raydium', methods=['GET', 'POST'])
def raydium():
    url = "https://api.raydium.io/v2/ammV3/ammPools"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for error status codes

        data = response.json()
        amm_pools = []

        for pool in data['data']:
            pool_data = {
                "pool_id": pool['id'],
                "price": pool["price"],  # Uncomment and add relevant fields
                "tvl": pool["tvl"],
                # Add other relevant information if needed
            }
            # print(pool_data)
            amm_pools.append(pool_data)

        return render_template('raydium.html', pool_data=amm_pools)

    except requests.exceptions.RequestException as e:
        print("Error fetching data:", e)
        return render_template('raydium.html', amm_pools=[])


@app.route('/summary')
def summary():
    searchTicker = request.args.get('user_input', 'SOL').lower()
    data = [(f"{pair.pair_address[-5:]}({pair.chain_id})", pair.liquidity.usd) for pair in client.search_pairs(searchTicker)]
    df = pd.DataFrame(data, columns=['Network', 'Liquidity'])

    summary = {
        'Total Networks': df.shape[0],
        'Total Liquidity': df['Liquidity'].sum(),
        'Average Liquidity': df['Liquidity'].mean(),
        'Minimum Liquidity': df['Liquidity'].min(),
        'Maximum Liquidity': df['Liquidity'].max(),
        'Standard Deviation': df['Liquidity'].std()
    }

    formatted_summary = {key: f"${value:,.2f}" if key != 'Total Networks' else value for key, value in summary.items()}

    return render_template('summary.html', summary=formatted_summary, user_input=searchTicker)


@app.route('/base')
def base():
    searchTicker = request.args.get('user_input', 'SOL').lower()
    return render_template('base.html', user_input=searchTicker)


@app.route('/token_summary')
def token_summary():
    searchTicker = request.args.get('user_input', 'SOL').lower()
    search = client.search_pairs(searchTicker)

    tokens = []
    for TokenPair in search:
        m5_change_style = get_price_change_style(TokenPair.price_change.m5)
        h1_change_style = get_price_change_style(TokenPair.price_change.h1)
        h6_change_style = get_price_change_style(TokenPair.price_change.h6)
        h24_change_style = get_price_change_style(TokenPair.price_change.h24)

        tokens.append({
            'chain_id': TokenPair.chain_id,
            'pair_address': TokenPair.pair_address,
            'liquidity_usd': "{:,.0f}".format(TokenPair.liquidity.usd),
            'quote_token_symbol': TokenPair.quote_token.symbol,
            'price_native': "{:,.2f}".format(TokenPair.price_native),
            'base_token_symbol': TokenPair.base_token.symbol,
            'price_usd': "{:,.2f}".format(TokenPair.price_usd),
            'volume_m5': "{:,.2f}".format(TokenPair.volume.m5),
            'm5_change': "{:.2f}".format(TokenPair.price_change.m5),
            'h1_change': "{:.2f}".format(TokenPair.price_change.h1),
            'h6_change': "{:.2f}".format(TokenPair.price_change.h6),
            'h24_change': "{:.2f}".format(TokenPair.price_change.h24),
            'volume_h1': "{:,.2f}".format(TokenPair.volume.h1),
            'volume_h6': "{:,.2f}".format(TokenPair.volume.h6),
            'volume_h24': "{:,.2f}".format(TokenPair.volume.h24),
            'm5_change_style': m5_change_style,
            'h1_change_style': h1_change_style,
            'h6_change_style': h6_change_style,
            'h24_change_style': h24_change_style,
        })
        # print(tokens)
        # SQL Input if wanted
        # insert_sql = "INSERT INTO token_pairs (chain_id, pair_address, liquidity_usd, quote_token_symbol, price_native, base_token_symbol, price_usd, volume_m5, m5_change, h1_change, h6_change, h24_change, volume_h1, volume_h6, volume_h24, m5_change_style, h1_change_style, h6_change_style, h24_change_style) VALUES " + ", ".join(tokens) + ";"

    return render_template('token_summary.html', tokens=tokens, user_input=searchTicker)

import re

# Configure static folder (replace 'static' with your actual folder name)
app.config['STATIC_FOLDER'] = 'static'


@app.route('/process-data', methods=['POST'])
def process_data():
    print('process data awake')
    try:
        data = request.get_json()
        token_pair_address = data.get('tokenPairAddress')
        # base_token = data.get('cardTitle')
        
        base_token = request.args.get('user_input', 'SOL').lower()
        print(base_token)

        if not token_pair_address:
            return jsonify({"message": "Missing tokenPairAddress"}), 400

        search = client.search_pairs(token_pair_address)
        # can add another function here for coingecko?
    
        if isinstance(search, list):            
            for pair in search:
                # print('Initial pair data', pair)
                ##coingecko
                # print('pair address:', pair.pair_address)


                #buys and sells
                if pair.pair_address == token_pair_address:
                    
                    transactions = {
                        "m5": str(pair.transactions.m5),
                        "h1": str(pair.transactions.h1),
                        "h6": str(pair.transactions.h6),
                        "h24": str(pair.transactions.h24)
                    }
                    # print('before JSON', transactions)
                    transactionsJson = jsonify(transactions)
                    # print('after JSON', transactionsJson)

                    # Extract buys and sells values
                    transaction_data = {}
                    for time_interval, data in transactions.items():
                        match = re.match(r"buys=(\d+) sells=(\d+)", data)
                        if match:
                            transaction_data[time_interval] = {"buys": int(match.group(1)), "sells": int(match.group(2))}

                    # print(transaction_data)

                    # Create the chart (assuming you have libraries like matplotlib)
                    plt.clf()
                    time_intervals = list(transaction_data.keys())
                    buys = [data["buys"] for data in transaction_data.values()]
                    sells = [data["sells"] for data in transaction_data.values()]

                    width = 0.35

                    plt.bar(time_intervals, buys, width, label='Buys')
                    plt.bar(time_intervals, sells, width, bottom=buys, label='Sells')

                    plt.xlabel('Time Interval')
                    plt.ylabel('Transactions')
                    plt.title(f'Address: {token_pair_address.encode("utf-8") if isinstance(token_pair_address, str) else token_pair_address}')  # Handle potential encoding issues
                    plt.legend()

                    # Save the chart as a temporary file (consider a dedicated temporary directory)
                    with open(f'{app.config["STATIC_FOLDER"]}/transaction_chart.png', 'wb') as f:
                        plt.savefig(f, format='png')  # Specify format for clarity
                    
                    # Create response data for both index.html AND arb
                    response_data = {
                        'transactions': transactions,
                        'chart_url': '/transaction_chart.png',  # Assuming a route to serve the image
                        'pair_URL': pair.url,
                        'dex_id': pair.dex_id,
                        'chain_id': pair.chain_id,
                        'pair_address': pair.pair_address,
                        'base_token': pair.base_token.name,
                        'quote_token': pair.quote_token.name,
                        'liquidity_usd': pair.liquidity.usd,
                        'price_native': pair.price_native,
                        'price_usd' : pair.price_usd,
                        'volume_24h': pair.volume.h24                 
                    }
                    # print('response data', response_data)
                    return jsonify(response_data), 200

        else:
            try:
                transactions = {
                    "m5": str(search.transactions.m5),
                    "h1": str(search.transactions.h1),
                    "h6": str(search.transactions.h6),
                    "h24": str(search.transactions.h24)
                }
                return jsonify(transactions), 200
            except AttributeError:
                return jsonify({"message": "Invalid search object or missing transactions attribute"}), 500

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Error processing data"}), 500

# Route to serve the image from the static folder (optional)
@app.route('/transaction_chart.png')
def serve_image():
    try:
        return send_from_directory(app.config['STATIC_FOLDER'], 'transaction_chart.png')
    except FileNotFoundError:
        return jsonify({"message": "Image not found"}), 404


@app.route('/charts')
def charts():
    searchTicker = request.args.get('user_input', 'SOL').lower()
    search = client.search_pairs(searchTicker)

    if not search:
        return render_template('charts.html',
                               tree_liquidity_img=None,
                               pie_liquidity_img=None,
                               tree_volume_img=None,
                               pie_volume_img=None,
                               user_input=searchTicker)

    liquidityTicker = [(f"{pair.pair_address[-5:]}({pair.chain_id})", pair.liquidity.usd) for pair in search]
    volumeTicker = [(f"{pair.pair_address[-5:]}({pair.chain_id})", pair.volume.h24) for pair in search]

    tree_liquidity_img = tree_chart_liquidity(liquidityTicker)
    pie_liquidity_img = pie_chart_liquidity(liquidityTicker)
    tree_volume_img = tree_chart_volume(volumeTicker)
    pie_volume_img = pie_chart_volume(volumeTicker)

    return render_template('charts.html',
                           tree_liquidity_img=tree_liquidity_img,
                           pie_liquidity_img=pie_liquidity_img,
                           tree_volume_img=tree_volume_img,
                           pie_volume_img=pie_volume_img,
                           user_input=searchTicker)




if __name__ == '__main__':
    app.run(debug=True)