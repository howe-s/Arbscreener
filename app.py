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

# RUN FLASK
app = Flask(__name__)

# Single configuration block for all app settings
app.config.update(
    SECRET_KEY='your_secret_key',
    SQLALCHEMY_DATABASE_URI='sqlite:///users.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    STATIC_FOLDER='static',
    CACHING=True,
    CACHE_TYPE='simple'
)

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
# Gather token pairs without caching


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

    # Renamed variables to be more descriptive
    investment_amount = float(request.form.get('initial_investment', 10000))
    slippage_rate = float(request.form.get('slippage', 0.0005))
    transaction_fee = float(request.form.get('fee_percentage', 0.0003))
    contract_address = request.form.get('search', '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs')

    user_portfolio = None  # Renamed from user_purchases to better reflect its purpose

    with app.app_context():
        db_session = db.session  # Renamed for clarity
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
    app.run(debug=True)

