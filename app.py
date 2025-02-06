import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
)
from flask_login import (
    LoginManager,
    current_user
)
from flask_caching import Cache
from flask_migrate import Migrate
from dexscreener import DexscreenerClient
import pandas as pd
import matplotlib
matplotlib.use('Agg')  
from utils.models import db, User
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# RUN FLASK
app = Flask(__name__)

# Single configuration block for all app settings
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key-here'),
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///users.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    STATIC_FOLDER='static',
    CACHING=True,
    CACHE_TYPE='simple'
)

# Handle potential "postgres://" to "postgresql://" conversion (Railway specific)
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Single cache initialization
cache = Cache(app)

# Initialize logging once
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

client = DexscreenerClient()

# Initialize DB
db.init_app(app)
migrate = Migrate(app, db)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Initialize the database tables directly
with app.app_context():
    db.create_all()

# APPLICATION ROUTES
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template(
        'index.html', 
        is_logged_in=current_user.is_authenticated,
        arbitrage_opportunities=[]
    )

@app.route('/landing_page_data', methods=['POST'])
def fetch_arbitrage_opportunities():
    from utils.main_utils import process_arbitrage_data

    investment_amount = float(request.form.get('initial_investment', 10000))
    slippage_rate = float(request.form.get('slippage', 0.0005))
    transaction_fee = float(request.form.get('fee_percentage', 0.0003))
    contract_address = request.form.get('search', '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs')

    user_portfolio = None

    with app.app_context():
        db_session = db.session
        arbitrage_results = process_arbitrage_data(
            user_portfolio, 
            db_session, 
            investment_amount, 
            slippage_rate, 
            transaction_fee, 
            search_address=contract_address
        )
    
    return jsonify(arbitrage_results), 200

from utils.main_utils import client_handler
@app.route('/get_logs', methods=['GET'])
def get_logs():
    logs = client_handler.get_logs()
    return jsonify(logs)

if __name__ == '__main__':
    # Use PORT environment variable for Railway
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

