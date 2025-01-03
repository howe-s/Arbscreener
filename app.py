from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
    send_file,
    send_from_directory
)
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user
)
from flask_caching import Cache
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime
import requests
from dexscreener import DexscreenerClient
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server-side plotting
from utils.models import db, User, Purchase  # Ensure Purchase is imported
from utils.price_utils import get_price_change_style
from utils.chart_utils import (
    tree_chart_liquidity,
    pie_chart_liquidity,
    tree_chart_volume,
    pie_chart_volume,
    generate_bar_chart
)
from utils.api_utils import rate_limit, fetch_current_price
from collections import Counter, defaultdict
import time
from flask_caching import Cache



# RUN FLASK
app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})  # Simple cache in memory, for production, consider Redis or Memcached
client = DexscreenerClient()
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with your secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['STATIC_FOLDER'] = 'static'

# Configuration for caching
app.config['CACHING'] = True
app.config['CACHE_TYPE'] = 'simple'  # Use 'simple' for in-memory caching, adjust as needed
cache = Cache(app)

# Initialize DB
db.init_app(app)
migrate = Migrate(app, db)
# Gather token pairs without caching


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

@cache.memoize(timeout=3600)  # Cache for 1 hour
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

# APPLICATION ROUTES
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
        # THIS WORKS
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

    from utils.user_profile_utils import (    
    gather_token_pairs_from_purchases,
    find_arbitrage_opportunities_for_user,
    filter_and_process_opportunities,
    match_pairs_with_opportunities,
    find_third_contract_data,
)
    logging.info('Processing user profile request')
    
    unique_pair_addresses = []
    
    # Initial values
    initial_investment = 1000  # Example value, adjust as needed
    slippage_pair1 = 0.005  # Example value
    slippage_pair2 = 0.005  # Example value
    fee_percentage = 0.003  # Example value, this is typically 0.3% for many DEXs

    searchTicker = request.args.get('user_input', 'WBTC').lower()
    user_purchases = Purchase.query.filter_by(user_id=current_user.id).all()
      
    session = db.session
    token_pairs = gather_token_pairs_from_purchases(user_purchases, session)
    
    logging.info('Finding arbitrage opportunities')
    arbitrage_opportunities = find_arbitrage_opportunities_for_user(token_pairs, user_purchases, slippage_pair1, slippage_pair2, fee_percentage, initial_investment)
    logging.info(f'Found {len(arbitrage_opportunities)} initial arbitrage opportunities.')

    # Process opportunities 
    quote_pairs, pair_chains = filter_and_process_opportunities(arbitrage_opportunities)
    logging.info(f'After filtering, {len(quote_pairs)} quote pairs and {len(pair_chains)} pair chains remain.')

    # Match pairs with opportunities
    opportunities_with_pairs = match_pairs_with_opportunities(arbitrage_opportunities, quote_pairs, pair_chains)
    logging.info(f'Matched pairs result in {len(opportunities_with_pairs)} opportunities.')

    # Debugging print statements
    logging.debug(f"Total combined opportunities and pairs: {len(opportunities_with_pairs)}")
    if opportunities_with_pairs:
        sample_combined = opportunities_with_pairs[0]
        all_pair_addresses = list(set(p.pair_address for o in opportunities_with_pairs for p in o['matching_pairs']))
        unique_pair_addresses = sorted(all_pair_addresses)

    # Use the initially defined values here
    logging.info('Finding third contract data')
    with app.app_context(): 
        session = db.session       
        all_three_contracts = find_third_contract_data(unique_pair_addresses, arbitrage_opportunities, session, initial_investment, slippage_pair1, slippage_pair2, fee_percentage)
    # print('ALL THREE CONTRACTS', all_three_contracts)
    sorted_opportunities = sorted(all_three_contracts, key=lambda x: x['int_profit'], reverse=True)
    logging.info(f'Final number of arbitrage opportunities: {len(sorted_opportunities)}')
    # print("API calls made:", api_call_counter)
    return render_template(
        'userProfile.html',
        user_input=searchTicker,
        name=current_user.username,
        full_name=current_user.full_name,
        is_logged_in=current_user.is_authenticated,
        arbitrage_opportunities=sorted_opportunities,
        search=token_pairs if token_pairs else None
    )
import logging
# logging.basicConfig(level=logging.DEBUG)

@app.route('/add_purchase', methods=['POST'])
@login_required
def add_purchase():
    from utils.models import Purchase
    # import logging
    # logging.debug("Form submitted")
    asset_name = request.form.get('asset_name')
    baseToken_address = request.form.get('baseToken_address')
    if not all([asset_name, baseToken_address]):
        flash('All fields are required.')
        # logging.debug("Validation failed: missing fields")
        return redirect(url_for('userProfile'))

    new_purchase = Purchase(
        user_id=current_user.id,
        asset_name=asset_name,
        baseToken_address=baseToken_address
    )
    db.session.add(new_purchase)
    db.session.commit()
    cache.delete_memoized(userProfile)  # Clear cache for userProfile
    flash('Purchase added successfully.')
    return redirect(url_for('userProfile'))

@app.route('/delete_purchase/<int:purchase_id>', methods=['POST'])
@login_required
def delete_purchase(purchase_id):
    from utils.models import Purchase
    purchase = Purchase.query.get(purchase_id)
    if purchase and purchase.user_id == current_user.id:
        db.session.delete(purchase)
        db.session.commit()
        cache.delete_memoized(userProfile)  # Clear cache for userProfile
        flash('Purchase deleted successfully.')
    else:
        flash('Purchase not found or unauthorized.')

    return redirect(url_for('userProfile'))

@app.route('/edit_purchase/<int:purchase_id>', methods=['GET', 'POST'])
@login_required
def edit_purchase(purchase_id):
    from utils.models import Purchase
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

@app.route('/user_prices/<int:purchase_id>', methods=['GET'])
@login_required
@cache.cached(timeout=300)  # Cache for 5 minutes
def user_prices(purchase_id):
    print('Getting prices...')  
    from utils.models import Purchase
    from utils.api_utils import fetch_current_price
      
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
    purchase.tokenPair = token_price_data['tokenPair']
    
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

@app.route('/dex_search', methods=['GET', 'POST'])
@login_required
# @cache.cached(timeout=600)  # Cache for 10 minutes
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

@app.route('/arb', methods=['GET', 'POST'])
@login_required
@cache.cached(timeout=300)  # Cache for 5 minutes
def arb():

    from utils.user_profile_utils import (   
        find_arbitrage_opportunities, 
        process_token_pairs
    )
    searchTicker = request.args.get('user_input', 'WBTC').lower()
    search = client.search_pairs(searchTicker)
    
    token_pairs = process_token_pairs(search)
    # DEFAULT ARB PAGE VALUES
    slippage_pair1 = 0.03  # 1% slippage
    slippage_pair2 = 0.03 # 1% slippage
    fee_percentage = 0.001  # 0.3% trading fee
    initial_investment = 10000  # Example initial investment

    arbitrage_opportunities = find_arbitrage_opportunities(
        token_pairs, slippage_pair1, slippage_pair2, fee_percentage, initial_investment
    )
    
    sorted_opportunities = sorted(arbitrage_opportunities, key=lambda x: x['int_profit'], reverse=True)
    return render_template('arb.html', search=search, user_input=searchTicker, arbitrage_opportunities=sorted_opportunities, is_logged_in=current_user.is_authenticated)

@app.route('/trending', methods=['GET', 'POST'])
@cache.cached(timeout=600)  # Cache for 10 minutes
def trending():
    #Passing the initial data
    searchTicker = request.args.get('user_input', 'WBTC').lower()
    search = client.search_pairs(searchTicker)
    
    return render_template('trending.html', search=search, user_input=searchTicker, is_logged_in=current_user.is_authenticated)

@app.route('/raydium', methods=['GET', 'POST'])
@login_required
@cache.cached(timeout=1200)  # Cache for 20 minutes
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
            amm_pools.append(pool_data)

        return render_template('raydium.html', pool_data=amm_pools, is_logged_in=current_user.is_authenticated)

    except requests.exceptions.RequestException as e:
        print("Error fetching data:", e)
        return render_template('raydium.html', amm_pools=[], is_logged_in=current_user.is_authenticated)

@app.route('/summary')
@login_required
@cache.cached(timeout=600)  # Cache for 10 minutes
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
@login_required
@cache.cached(timeout=300)  # Cache for 5 minutes
def base():
    searchTicker = request.args.get('user_input', 'WBTC').lower()
    return render_template('base.html', user_input=searchTicker, is_logged_in=current_user.is_authenticated)

@app.route('/token_table')
@login_required
@cache.cached(timeout=600)  # Cache for 10 minutes
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

    return render_template('token_table.html', tokens=tokens, user_input=searchTicker, is_logged_in=current_user.is_authenticated)
    
@app.route('/process-data', methods=['POST'])
@login_required
def process_data():
    print('process data awake')
    try:
        data = request.get_json()
        token_pair_address = data.get('tokenPairAddress')
        base_token = request.args.get('user_input', 'WBTC').lower()

        if not token_pair_address:
            return jsonify({"message": "Missing tokenPairAddress"}), 400

        search = client.search_pairs(token_pair_address)
    
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
@login_required
@cache.cached(timeout=1200)  # Cache for 20 minutes
def charts():
    searchTicker = request.args.get('user_input').lower() 
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