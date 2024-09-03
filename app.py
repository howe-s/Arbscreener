import subprocess
import sys

# Install Packages
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Required Packages
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
    'jinja2',
    'flask-cors',
    'flask_sqlalchemy',
    'flask_login',
    'werkzeug',
    'flask_migrate',
    'markupsafe'
]

# Check if packages installed, if not, install
for package in required_packages:
    try:
        __import__(package.split('==')[0])
    except ImportError:
        install(package)

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime
import time
import requests
from dexscreener import DexscreenerClient
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
import squarify
import pandas as pd
from flask_cors import CORS
import plotly.graph_objs as go
import plotly.io as pio
import math
from jinja2 import Environment
from markupsafe import Markup
from html import escape
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server-side plotting
from models import db, User, Purchase  # Ensure Purchase is imported


#RUN FLASK
app = Flask(__name__)
client = DexscreenerClient()
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with your secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#Initialize DB
db.init_app(app)
migrate = Migrate(app, db)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize the database tables directly
with app.app_context():
    db.create_all()

# HELPER FUNCTIONS
def runTime(func):
    def wrapper():
        timeOne = time.time()
        func()
        timeTwo = time.time()-timeOne
        print(f'{func.__name__} ran in '\
              f'{timeTwo} seconds')
    return wrapper

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

def generate_bar_chart(x_data, y_data, title="Volume Chart", x_label="Time Frame", y_label="Volume"):
    # Construct data
    data = [
        go.Bar(
            x=x_data,
            y=y_data
        )
    ]

    # Define the layout
    layout = go.Layout(
        title=title,
        xaxis=dict(title=x_label),
        yaxis=dict(title=y_label)
    )

    # Create figure
    fig = go.Figure(data=data, layout=layout)

    # Convert to HTML div string
    chart_div = pio.to_html(fig, full_html=False)

    return chart_div

def format_number(value, decimals=0, thousands_sep=',', decimal_sep='.'):
    formatted_value = f"{value:,.{decimals}f}"
    return Markup(escape(formatted_value))

#APPLICATION ROUTES
@app.route('/', methods=['GET', 'POST'])
def index():
 
    return render_template('index.html', is_logged_in=current_user.is_authenticated)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('userProfile'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']

        # Check if the username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.')
            return redirect(url_for('register'))

        # Create a new user with hashed password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password, full_name=full_name)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/userProfile')
@login_required
def userProfile():
    searchTicker = request.args.get('user_input', 'WBTC').lower()

    # DEFAULT ARB PAGE VALUES
    slippage_pair1 = 0.03
    slippage_pair2 = 0.03
    fee_percentage = 0.001
    initial_investment = 2.0

    # Fetch all baseToken_address associated with the logged-in user's purchases
    user_purchases = Purchase.query.filter_by(user_id=current_user.id).all()
    baseToken_addresses = [purchase.baseToken_address for purchase in user_purchases]
    print('Base token addresses:', baseToken_addresses)
    
    # Accumulate arbitrage opportunities for all base token addresses
    all_arbitrage_opportunities = []
    search_result = None

    for address in baseToken_addresses:
        search = client.search_pairs(address)
        if search:
            search_result = search
            token_pairs = process_token_pairs(search)

            # Find arbitrage opportunities for this set of token pairs
            arbitrage_opportunities = find_arbitrage_opportunities(
                token_pairs, slippage_pair1, slippage_pair2, fee_percentage, initial_investment, user_purchases
            )

            all_arbitrage_opportunities.extend(arbitrage_opportunities)

            ##### YOU STOPPED HERE ##############
            # for arb in all_arbitrage_opportunities:
            #     nativePrice_difference = arb['nativePrice_difference']
            #     userArb_profit = nativePrice_difference * user_purchases.quantity
            #     print(userArb_profit)
            ############################################################

    # Sort opportunities after the loop
    sorted_opportunities = sorted(all_arbitrage_opportunities, key=lambda x: x['int_profit'], reverse=True)    
   
    # Return based on whether search results were found
    if search_result:
        return render_template(
            'userProfile.html',
            user_input=searchTicker,
            name=current_user.username,
            full_name=current_user.full_name,
            is_logged_in=current_user.is_authenticated,
            arbitrage_opportunities=sorted_opportunities,
            search=search_result
        )
    else:
        return render_template(
            'userProfile.html',
            user_input=searchTicker,
            name=current_user.username,
            full_name=current_user.full_name,
            is_logged_in=current_user.is_authenticated,
            arbitrage_opportunities=sorted_opportunities
        )



@app.route('/add_purchase', methods=['POST'])
@login_required
def add_purchase():
    asset_name = request.form.get('asset_name')
    quantity = request.form.get('quantity')
    purchase_price = request.form.get('purchase_price')
    purchase_date = request.form.get('purchase_date')
    baseToken_address = request.form.get('baseToken_address')
    if not all([asset_name, quantity, purchase_price, purchase_date, baseToken_address]):
        flash('All fields are required.')
        return redirect(url_for('userProfile'))

    try:
        quantity = float(quantity)
        purchase_price = float(purchase_price)
        purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid input values.')
        return redirect(url_for('userProfile'))
    
    new_purchase = Purchase(
        user_id=current_user.id,
        asset_name=asset_name,
        quantity=quantity,
        purchase_price=purchase_price,
        purchase_date=purchase_date,
        baseToken_address=baseToken_address
    )

    db.session.add(new_purchase)
    db.session.commit()

    flash('Purchase added successfully.')
    return redirect(url_for('userProfile'))


@app.route('/delete_purchase/<int:purchase_id>', methods=['POST'])
@login_required
def delete_purchase(purchase_id):
    purchase = Purchase.query.get(purchase_id)
    if purchase and purchase.user_id == current_user.id:
        db.session.delete(purchase)
        db.session.commit()
        flash('Purchase deleted successfully.')
    else:
        flash('Purchase not found or unauthorized.')

    return redirect(url_for('userProfile'))


@app.route('/edit_purchase/<int:purchase_id>', methods=['GET', 'POST'])
@login_required
def edit_purchase(purchase_id):
    purchase = Purchase.query.get(purchase_id)
    if purchase and purchase.user_id == current_user.id:
        if request.method == 'POST':
            # Update the purchase details
            purchase.asset_name = request.form['asset_name']
            purchase.baseToken_address = request.form['baseToken_address']
            purchase.quantity = float(request.form['quantity'])
            purchase.purchase_price = float(request.form['purchase_price'])
            purchase.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d')

            db.session.commit()
            flash('Purchase updated successfully.')
            return redirect(url_for('userProfile'))

        return render_template('edit_purchase.html', purchase=purchase)
    else:
        flash('Purchase not found or unauthorized.')
        return redirect(url_for('userProfile'))

# Global variable to track the time of the last API request
last_request_time = 0
request_delay = 7  # seconds

def rate_limit():
    global last_request_time
    current_time = time.time()
    if current_time - last_request_time < request_delay:
        time.sleep(request_delay - (current_time - last_request_time))
    last_request_time = time.time()
    return None

def fetch_current_price(asset_name):
    print('Fetching current price...')
    searchTicker = asset_name.lower()
    rate_limit()
    search = client.search_pairs(searchTicker)
    # search = client.search_pairs(tokenLowerCase)
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

def fetch_historical_price(asset_name, start_timestamp, end_timestamp):
    print('Fetching historical price...')
    rate_limit()
    responseHistoricalPrice = requests.get(f'https://api.coincap.io/v2/assets/{asset_name}/history?interval=d1&start={start_timestamp}&end={end_timestamp}')
    if responseHistoricalPrice.status_code == 200:
        try:
            data = responseHistoricalPrice.json()['data']
            # print('historical price data', data)
            return data
        except KeyError:
            print('Error parsing historical price data.')
            return None
    else:
        print(f'Error fetching historical price: {responseHistoricalPrice.status_code}')
        return None


def date_to_timestamp(date_str):
    # Parse the date string to a datetime object
    dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

    # Convert the datetime object to a timestamp in seconds
    timestamp_seconds = int(time.mktime(dt.timetuple()))

    # Convert the timestamp to milliseconds
    timestamp_milliseconds = timestamp_seconds * 1000

    return timestamp_milliseconds

@app.route('/user_prices/<int:purchase_id>', methods=['GET'])
@login_required
def user_prices(purchase_id):
    print('Getting prices...')  
      
    # Helper function to calculate profit and percentages
    def calculate_profit_and_percentages(token_price, purchase_price, quantity):
        profit = round(float(token_price - purchase_price), 2)
        profit_percentage = round(float(((token_price - purchase_price) / purchase_price) * 100), 2)
        purchase_cost = round(float(purchase_price * quantity), 2)
        return profit, profit_percentage, purchase_cost

    purchase = Purchase.query.get(purchase_id)
    if not purchase:
        return {'error': 'Purchase not found'}, 404
    # GET tokenPrice data through helper function with User db saved quote_address
    token_price_data = fetch_current_price(purchase.baseToken_address)
    token_price = token_price_data['price']
    if token_price is None:
        return {'error': 'Could not fetch asset price'}, 500
    # passing new token_price data through helper function
    profit, profit_percentage, purchase_cost = calculate_profit_and_percentages(
        token_price, purchase.purchase_price, purchase.quantity
    )
    
    # Update the purchase model's (database's) pair_address and source fields
    purchase.pair_address = token_price_data['pairAddress'] or 'None'
    purchase.source = token_price_data['source']
    purchase.pair_url = token_price_data['pair_url']
    purchase.baseToken_url = token_price_data['baseToken_url']
    
    db.session.commit()

    currentValue = token_price * purchase.quantity
    return {
        'purchase_id': purchase_id,
        'tokenPrice': token_price,
        'purchasePrice': purchase.purchase_price,
        'profit': profit,
        'profitPercentage': profit_percentage,
        'purchaseCost': purchase_cost,
        'source': token_price_data['source'],
        'name': token_price_data['name'],
        'quantity': purchase.quantity,
        'tokenPair': token_price_data['tokenPair'],
        'currentValue': currentValue,
        'chain_id': token_price_data['chain_id']
    }

#This route loads the data on dex_search and renders the page 
@app.route('/dex_search', methods=['GET', 'POST'])
@login_required
def dex_search():
    # Get the user input for ticker and perform the search
    searchTicker = request.args.get('user_input', 'WBTC').lower()    
    search = client.search_pairs(searchTicker)
    
    pool_data = []
 
    for TokenPair in search:
        # chart
            # Example data
        x_data = ['5m', '1h', '6h', '24h']
        y_data = [TokenPair.volume.m5, TokenPair.volume.h1, TokenPair.volume.h6, TokenPair.volume.h24]

        # Generate the bar chart
        chart_div = generate_bar_chart(x_data, y_data)
        
        # print(TokenPair.liquidity)
        pool_data.append({
            'chain_id': TokenPair.chain_id,
            'dex_id': TokenPair.dex_id,
            'liquidity': TokenPair.liquidity,
            'liquidity_usd_formatted': f"${TokenPair.liquidity.usd:,.2f}",
            'liquidity_base_formatted': f"{TokenPair.liquidity.base:,.2f}",
            'liquidity_quote_formatted': f"{TokenPair.liquidity.quote:,.2f}",            
            'price_native': TokenPair.price_native,
            'price_native_formatted': f"${TokenPair.price_native:,.2f}",
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
            'base_token': TokenPair.base_token.symbol,
            'pair_url': TokenPair.url,
            'baseToken_address': TokenPair.base_token.address,
            'quoteToken_address': TokenPair.quote_token.address
            
        })

    sorted_pool = sorted(pool_data, key=lambda x: x['volume_24h'], reverse=True)
    # Pass the data to the template
    return render_template('dex_search.html', pool_data=sorted_pool, user_input=searchTicker, chart_div=chart_div, is_logged_in=current_user.is_authenticated)


# arb helper function
def calculate_arbitrage_profit(initial_investment, price_pair1, price_pair2, slippage_pair1, slippage_pair2, fee_percentage):
    # Convert initial investment to units of the first pair
    amount_pair1 = initial_investment / price_pair1
    
    # Apply slippage for the first pair
    adjusted_amount_pair1 = amount_pair1 * (1 - slippage_pair1)
    
    # Convert the adjusted amount to the value in the second pair
    value_pair2 = adjusted_amount_pair1 * price_pair2
    
    # Apply slippage for the second pair
    final_amount_pair2 = value_pair2 * (1 - slippage_pair2)
    
    # Calculate the fees (assuming fee percentage is for both trades)
    fees = initial_investment * fee_percentage * 2  # Two trades
    
    # Calculate profit
    profit = final_amount_pair2 - initial_investment - fees
    # print('profit?', profit)
    
    return profit

## helper sort
def myFunc(e):
  return e['profit']


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

@app.route('/arb', methods=['GET', 'POST'])
@login_required
def arb():
    searchTicker = request.args.get('user_input', 'WBTC').lower()
    search = client.search_pairs(searchTicker)
    
    token_pairs = process_token_pairs(search)
    # DEFAULT ARB PAGE VALUES
    slippage_pair1 = 0.03  # 1% slippage
    slippage_pair2 = 0.03 # 1% slippage
    fee_percentage = 0.001  # 0.3% trading fee
    initial_investment = 1000  # Example initial investment

    arbitrage_opportunities = find_arbitrage_opportunities(
        token_pairs, slippage_pair1, slippage_pair2, fee_percentage, initial_investment, user_purchases
    )
    
    sorted_opportunities = sorted(arbitrage_opportunities, key=lambda x: x['int_profit'], reverse=True)
    return render_template('arb.html', search=search, user_input=searchTicker, arbitrage_opportunities=sorted_opportunities, is_logged_in=current_user.is_authenticated)


@app.route('/trending', methods=['GET', 'POST'])
def trending():
    #Passing the initial data
    searchTicker = request.args.get('user_input', 'WBTC').lower()
    search = client.search_pairs(searchTicker)
    
    return render_template('trending.html', search=search, user_input=searchTicker, is_logged_in=current_user.is_authenticated)

@app.route('/raydium', methods=['GET', 'POST'])
@login_required
def raydium():
    url = "https://api.raydium.io/v2/ammV3/ammPools"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for error status codes

        data = response.json()
        amm_pools = []

        for pool in data['data']:
            print(pool)
            pool_data = {
                "pool_id": pool['id'],
                "price": pool["price"],  # Uncomment and add relevant fields
                "tvl": pool["tvl"],
                # Add other relevant information if needed
            }
            # print(pool_data)
            amm_pools.append(pool_data)

        return render_template('raydium.html', pool_data=amm_pools, is_logged_in=current_user.is_authenticated)

    except requests.exceptions.RequestException as e:
        print("Error fetching data:", e)
        return render_template('raydium.html', amm_pools=[], is_logged_in=current_user.is_authenticated)


@app.route('/summary')
@login_required
def summary():
    searchTicker = request.args.get('user_input', 'WBTC').lower()
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

    return render_template('summary.html', summary=formatted_summary, user_input=searchTicker, is_logged_in=current_user.is_authenticated)


@app.route('/base')
def base():
    searchTicker = request.args.get('user_input', 'WBTC').lower()
    return render_template('base.html', user_input=searchTicker, is_logged_in=current_user.is_authenticated)


@app.route('/token_table')
@login_required
def token_table():
    print('token_table route pinged')
    searchTicker = request.args.get('user_input', 'WBTC').lower()
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

        # SQL Input if wanted
        # insert_sql = "INSERT INTO token_pairs (chain_id, pair_address, liquidity_usd, quote_token_symbol, price_native, base_token_symbol, price_usd, volume_m5, m5_change, h1_change, h6_change, h24_change, volume_h1, volume_h6, volume_h24, m5_change_style, h1_change_style, h6_change_style, h24_change_style) VALUES " + ", ".join(tokens) + ";"

    return render_template('token_table.html', tokens=tokens, user_input=searchTicker, is_logged_in=current_user.is_authenticated)
    

import re

# Configure static folder (replace 'static' with your actual folder name)
app.config['STATIC_FOLDER'] = 'static'


@app.route('/process-data', methods=['POST'])
@login_required
def process_data():
    print('process data awake')
    try:
        data = request.get_json()
        token_pair_address = data.get('tokenPairAddress')
        # base_token = data.get('cardTitle')
        
        base_token = request.args.get('user_input', 'WBTC').lower()
        print(base_token)

        if not token_pair_address:
            return jsonify({"message": "Missing tokenPairAddress"}), 400

        search = client.search_pairs(token_pair_address)
        # can add another function here for coingecko?
    
        if isinstance(search, list):            
            for pair in search:
                if pair.pair_address == token_pair_address:
                    
                    transactions = {
                        "m5": str(pair.transactions.m5),
                        "h1": str(pair.transactions.h1),
                        "h6": str(pair.transactions.h6),
                        "h24": str(pair.transactions.h24)
                    }

                    x_data = ['5m', '1h', '6h', '24h']
                    y_data = [pair.volume.m5, pair.volume.h1, pair.volume.h6, pair.volume.h24]

                    # Generate the interactive chart
                    chart_div = generate_bar_chart(x_data, y_data)

                    # Prepare response data
                    response_data = {
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
                        'x_data': ['5m', '1h', '6h', '24h'],
                        'y_data': [pair.volume.m5, pair.volume.h1, pair.volume.h6, pair.volume.h24],                
                    }

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

@app.route('/charts')
def charts():
    searchTicker = request.args.get('user_input', 'WBTC').lower()
    search = client.search_pairs(searchTicker)

    if not search:
        return render_template('charts.html',
                               tree_liquidity_img=None,
                               pie_liquidity_img=None,
                               tree_volume_img=None,
                               pie_volume_img=None,
                               user_input=searchTicker,
                               is_logged_in=current_user.is_authenticated)

    # Sort liquidityData by pair.liquidity.usd in descending order
    liquidityData = sorted(
        [(f"{pair.pair_address[-5:]}({pair.chain_id})", pair.liquidity.usd) for pair in search],
        key=lambda x: x[1],
        reverse=True
    )

    # Sort volumeData by pair.volume.h24 in descending order
    volumeData = sorted(
        [(f"{pair.pair_address[-5:]}({pair.chain_id})", pair.volume.h24) for pair in search],
        key=lambda x: x[1],
        reverse=True
    )

    tree_liquidity_img = tree_chart_liquidity(liquidityData)
    pie_liquidity_img = pie_chart_liquidity(liquidityData)
    tree_volume_img = tree_chart_volume(volumeData)
    pie_volume_img = pie_chart_volume(volumeData)

    return render_template('charts.html',
                           tree_liquidity_img=tree_liquidity_img,
                           pie_liquidity_img=pie_liquidity_img,
                           tree_volume_img=tree_volume_img,
                           pie_volume_img=pie_volume_img,
                           user_input=searchTicker,
                           is_logged_in=current_user.is_authenticated)




if __name__ == '__main__':
    app.run(debug=True)
