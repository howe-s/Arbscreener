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
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# RUN FLASK
app = Flask(__name__)

# Determine if we're running on Railway
is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
logger.info(f"Running in {'production' if is_production else 'development'} mode")

# Database configuration
if is_production:
    # Get individual connection parameters
    db_user = os.getenv('PGUSER')
    db_password = os.getenv('PGPASSWORD')
    db_host = os.getenv('PGHOST')
    db_port = os.getenv('PGPORT')
    db_name = os.getenv('PGDATABASE')
    
    if not all([db_user, db_password, db_host, db_port, db_name]):
        logger.error("Missing database connection parameters")
        raise ValueError("Database connection parameters are required in production")
    
    # Construct the database URL
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    logger.info("Using PostgreSQL database")
    
    # Test the database connection
    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            logger.info("Successfully connected to the database")
    except OperationalError as e:
        logger.error(f"Failed to connect to the database: {str(e)}")
        raise
else:
    # Use SQLite locally
    db_url = 'sqlite:///users.db'
    logger.info("Using SQLite database")

logger.info(f"Database URL: {db_url}")

# Single configuration block for all app settings
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key-here'),
    SQLALCHEMY_DATABASE_URI=db_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        'pool_size': 5,
        'pool_timeout': 30,
        'pool_recycle': 1800,
    },
    STATIC_FOLDER='static',
    CACHING=True,
    CACHE_TYPE='simple'
)

logger.info("App configuration complete")

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return jsonify({"error": "Internal Server Error", "details": str(error)}), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"Not Found Error: {error}")
    return jsonify({"error": "Not Found", "details": str(error)}), 404

# Single cache initialization
cache = Cache(app)
logger.info("Cache initialized")

client = DexscreenerClient()

# Initialize DB
db.init_app(app)
migrate = Migrate(app, db)
logger.info("Database initialized")

# Setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
logger.info("Login manager initialized")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Initialize the database tables directly
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# APPLICATION ROUTES
@app.route('/', methods=['GET', 'POST'])
def index():
    logger.info("Handling request to index route")
    try:
        return render_template(
            'index.html', 
            is_logged_in=current_user.is_authenticated,
            arbitrage_opportunities=[]
        )
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/landing_page_data', methods=['POST'])
def fetch_arbitrage_opportunities():
    logger.info("Handling request to fetch arbitrage opportunities")
    try:
        from utils.main_utils import process_arbitrage_data

        investment_amount = float(request.form.get('initial_investment', 10000))
        slippage_rate = float(request.form.get('slippage', 0.0005))
        transaction_fee = float(request.form.get('fee_percentage', 0.0003))
        contract_address = request.form.get('search', '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs')

        logger.debug(f"Processing request with parameters: investment={investment_amount}, slippage={slippage_rate}, fee={transaction_fee}, contract={contract_address}")

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
    except Exception as e:
        logger.error(f"Error in fetch_arbitrage_opportunities: {e}")
        return jsonify({"error": str(e)}), 500

from utils.main_utils import client_handler
@app.route('/get_logs', methods=['GET'])
def get_logs():
    try:
        logs = client_handler.get_logs()
        return jsonify(logs)
    except Exception as e:
        logger.error(f"Error in get_logs: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Use PORT environment variable for Railway
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port)

