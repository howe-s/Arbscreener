from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    full_name = db.Column(db.String(150))
    portfolio_balance = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationships
    purchases = db.relationship('Purchase', backref='user', lazy=True)

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    asset_name = db.Column(db.String(100), nullable=False)
    baseToken_address = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # quantity = db.Column(db.Float, nullable=False)
    # purchase_price = db.Column(db.Float, nullable=False)
    # purchase_date = db.Column(db.Date, nullable=False)
    # pair_address = db.Column(db.String(100))  # Existing field
    # pair_url = db.Column(db.String(200))
    # baseToken_url = db.Column(db.String(200))
    # source = db.Column(db.String(50))  # New field for data source
    # tokenPair = db.Column(db.String(50))

    # Remove the explicit user relationship here to avoid conflict
    # user = db.relationship('User', backref=db.backref('purchases', lazy=True))

    def __repr__(self):
        return f'<Purchase {self.asset_name}>'
    
class Contracts(db.Model):
    __tablename__ = 'contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    contract_address = db.Column(db.String(255), unique=True, nullable=False)
    base_token_address = db.Column(db.String(255))
    quote_token_address = db.Column(db.String(255))
    chain_id = db.Column(db.String(50))
    dex_id = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime)
    price_native = db.Column(db.Float)
    price_usd = db.Column(db.Float)

    def __repr__(self):
        return f'<Contract {self.contract_address}>'
    
class ContractLake(db.Model):
    __tablename__ = 'lake'
    id = db.Column(db.Integer, primary_key=True)
    contract_address = db.Column(db.String(255), unique=True, nullable=False)
    base_token_address = db.Column(db.String(255))
    quote_token_address = db.Column(db.String(255))
    chain_id = db.Column(db.String(50))
    dex_id = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime)
    price_native = db.Column(db.Float)
    price_usd = db.Column(db.Float)  # I just added this

    def __repr__(self):
        return f'<Contract {self.contract_address}>'
