from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    full_name = db.Column(db.String(150))
    portfolio_balance = db.Column(db.Float, nullable=False, default=0.0)
    # Relationships
    purchases = db.relationship('Purchase', backref='user', lazy=True)

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    asset_name = db.Column(db.String(100), nullable=False)
    quote_address = db.Column(db.String(100)) 
    quantity = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    pair_address = db.Column(db.String(100))  # Existing field
    pair_url = db.Column(db.String(200))
    source = db.Column(db.String(50))  # New field for data source

    # Remove the explicit user relationship here to avoid conflict
    # user = db.relationship('User', backref=db.backref('purchases', lazy=True))

    def __repr__(self):
        return f'<Purchase {self.asset_name}>'
