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
def landing_page_data():
    from utils.main_utils import process_arbitrage_data

    # Retrieve form data
    initial_investment = float(request.form.get('initial_investment', 10000))
    slippage = float(request.form.get('slippage', 0.0005))
    fee_percentage = float(request.form.get('fee_percentage', 0.0003))
    address = request.form.get('search', '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs')

    # Since this isn't fetching user purchases, we'll use None or an empty list
    user_purchases = None  # or []

    with app.app_context():
        session = db.session
        # Pass the search address to handle the case without user purchases
        sorted_opportunities = process_arbitrage_data(user_purchases, session, initial_investment, slippage, fee_percentage, search_address=address)
    
    # print('SORTED OPPS:', sorted_opportunities)
    return jsonify(sorted_opportunities), 200

from utils.main_utils import client_handler
@app.route('/get_logs', methods=['GET'])
def get_logs():
    logs = client_handler.get_logs()
    return jsonify(logs)

if __name__ == '__main__':
    app.run(debug=True)

