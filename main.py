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
    'dexscreener'
]

# Check and install each package
for package in required_packages:
    try:
        __import__(package.split('==')[0])
    except ImportError:
        install(package)

from flask import Flask, render_template, request
from dexscreener import DexscreenerClient
import matplotlib

matplotlib.use('Agg')  # Use non-interactive backend for server-side plotting
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
import squarify
import pandas as pd

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


@app.route('/', methods=['GET', 'POST'])
def index():
    searchTicker = request.args.get('user_input', 'SOL').lower()
    search = client.search_pairs(searchTicker)

    if not search:
        return render_template('index.html', search=[], tree_liquidity_img=None, pie_liquidity_img=None,
                               tree_volume_img=None, pie_volume_img=None, user_input=searchTicker)

    liquidityTicker = [(f"{pair.pair_address[-5:]}({pair.chain_id})", pair.liquidity.usd) for pair in search]
    volumeTicker = [(f"{pair.pair_address[-5:]}({pair.chain_id})", pair.volume.h24) for pair in search]

    tree_liquidity_img = tree_chart_liquidity(liquidityTicker)
    pie_liquidity_img = pie_chart_liquidity(liquidityTicker)
    tree_volume_img = tree_chart_volume(volumeTicker)
    pie_volume_img = pie_chart_volume(volumeTicker)

    return render_template('index.html', search=search, tree_liquidity_img=tree_liquidity_img,
                           pie_liquidity_img=pie_liquidity_img, tree_volume_img=tree_volume_img,
                           pie_volume_img=pie_volume_img, user_input=searchTicker)


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

    return render_template('token_summary.html', tokens=tokens, user_input=searchTicker)


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
