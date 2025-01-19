# Crypto Arbitrage Detection System

A sophisticated Flask-based application that detects and analyzes arbitrage opportunities across cryptocurrency trading pairs in real-time. The system monitors price discrepancies across different exchanges and calculates potential profits while accounting for slippage, fees, and liquidity constraints.

![image](https://github.com/user-attachments/assets/ddd975d6-6b0d-4049-87e2-e670713be36d)

## Features

- Real-time arbitrage opportunity detection across multiple DEXes
- Slippage and trading fee considerations
- Liquidity analysis and validation
- Rate-limited API interactions with exponential backoff
- Caching system for frequently accessed data
- Support for triangular arbitrage opportunities
- User-specific arbitrage opportunity tracking
- Price change monitoring and updates
- Comprehensive profit calculation considering all trading costs

## Prerequisites

- Python 3.8+
- Flask
- SQLAlchemy
- DexScreener API access

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd crypto-arbitrage-detection
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
export FLASK_APP=app.py
export FLASK_ENV=development
```

## Configuration

The system accepts several configuration parameters that can be adjusted based on your needs:

- `initial_investment`: Starting amount for arbitrage calculations (default: 10000)
- `slippage_pair1`: Expected slippage for first pair (default: 0.0005)
- `slippage_pair2`: Expected slippage for second pair (default: 0.0005)
- `slippage_pair3`: Expected slippage for third pair (default: 0.0005)
- `fee_percentage`: Trading fee percentage (default: 0.0003)

## API Endpoints

### Landing Page Data
```python
POST /landing_page_data
```

Parameters:
- `initial_investment`: Float (default: 10000)
- `slippage_pair1`: Float (default: 0.0005)
- `slippage_pair2`: Float (default: 0.0005)
- `slippage_pair3`: Float (default: 0.0005)
- `fee_percentage`: Float (default: 0.0003)
- `search`: String (Wallet address)

Returns:
- JSON array of arbitrage opportunities sorted by profit potential

## Core Components

### 1. Arbitrage Detection
The system implements sophisticated arbitrage detection through several key components:

- `find_arbitrage_opportunities()`: Core algorithm for detecting price discrepancies
- `calculate_arbitrage_profit()`: Calculates potential profits considering all costs
- `check_price_compatibility()`: Validates price relationships across trading pairs

### 2. Data Management
Efficient data handling through:

- Rate-limited API calls with exponential backoff
- Caching system for frequently accessed data
- Database integration for persistent storage

### 3. Safety Features
Built-in protections including:

- Liquidity validation
- Slippage consideration
- Trading fee calculations
- Rate limiting for API calls

## Usage Example

```python
from flask import Flask
from utils.user_profile_utils import process_arbitrage_data

app = Flask(__name__)

@app.route('/landing_page_data', methods=['POST'])
def landing_page_data():
    initial_investment = 10000
    slippage = 0.0005
    fee_percentage = 0.0003
    
    opportunities = process_arbitrage_data(
        user_purchases=None,
        session=db.session,
        initial_investment=initial_investment,
        slippage_pair1=slippage,
        slippage_pair2=slippage,
        fee_percentage=fee_percentage
    )
    
    return jsonify(opportunities), 200
```

## Error Handling

The system implements comprehensive error handling:

- API rate limit management
- Connection error recovery
- Data validation
- Transaction safety checks

## Performance Optimization

Several optimizations are implemented:

- LRU caching for frequent calculations
- Batch processing of API requests
- Efficient data structures for quick lookups
- Smart update strategies for price changes

## Acknowledgments

- DexScreener API for providing real-time cryptocurrency data
- Flask community for the robust web framework
- SQLAlchemy team for the powerful ORM

## Project Background and Current State

This project initially started as portfolio and arbitrage alert application. However, due to the nature of finding second and third contracts, there is an inability to scale for a full portolfio using third party API data. The limitation is the amount of API calls required to compile a list of opprotunities for multiple assets with their updated and realtime pricing information. 

To address this, I have implemented a data lake mechanism to store lists of compatible contracts in SQL allowing for quick identification of second and third contracts for arbitrage opprotunities. However, I am still limited by the realtime pricing. I plan to implement non-validating nodes, network by network, for accurate contract liquidity states to determine real-time asset pricing without an external API. 






