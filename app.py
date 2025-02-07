import os
import sys
import time

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
)
from flask_caching import Cache
from dexscreener import DexscreenerClient
import pandas as pd
import matplotlib
matplotlib.use('Agg')  
import logging
from dotenv import load_dotenv

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

# Single configuration block for all app settings
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key-here'),
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

@app.errorhandler(Exception)
def handle_exception(error):
    logger.error(f"Unhandled Exception: {error}", exc_info=True)
    return jsonify({"error": "Internal Server Error", "details": str(error)}), 500

# Single cache initialization
cache = Cache(app)
logger.info("Cache initialized")

client = DexscreenerClient()

# APPLICATION ROUTES
@app.route('/', methods=['GET', 'POST'])
def index():
    logger.info("Handling request to index route")
    try:
        return render_template(
            'index.html', 
            is_logged_in=False,
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

        arbitrage_results = process_arbitrage_data(
            None,  # No user portfolio needed 
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
    try:
        # Use PORT environment variable for Railway
        port = int(os.getenv('PORT', 8080))
        logger.info(f"Starting application on port {port}")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        raise

# Health check endpoint
@app.route('/health')
def health_check():
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": time.time()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 500

