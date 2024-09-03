# Arbscreener Flask Application

## Overview

This project is a Flask-based web application that integrates with the Dexscreener API to display cryptocurrency token pair details. The application generates dynamic HTML content to visualize token liquidity, prices, and volumes, providing a user-friendly interface for exploring token data.

## Features

- **Dynamic Token Pair Cards:** Display token pair details including liquidity, price, and volume in an organized card format.
- **Interactive Summary Display:** Click on a token pair card to display detailed information in a fixed summary div.
- **Charts Visualization:** Generate pie and tree charts for liquidity and volume data using Matplotlib and Squarify.
- **Responsive Design:** The layout adapts to different screen sizes, ensuring a consistent user experience across devices.

## Project Structure


<!-- project-root/
├── main.py              # Main Flask application file
├── templates/           # HTML templates for the application
│   ├── base.html        # Base template for consistent layout
│   ├── index.html       # Main page displaying token pair cards
│   ├── charts.html      # Page displaying liquidity and volume charts
│   ├── summary.html     # Page displaying a summary of token pair data
│   ├── token_summary.html # Page displaying detailed token pair statistics
│   └── ...
├── static/              # Directory for static files (e.g., CSS, JavaScript)
│   ├── style.css        # Custom styles for the application
│   └── ...
├── README.md            # Project documentation
└── requirements.txt     # Python dependencies -->

### Documentation files
    project-root/
    ├── main.py              # Main Flask application file
    ├── templates/           # HTML templates for the application
    │   ├── base.html        # Base template for consistent layout
    │   ├── index.html       # Main page displaying token pair cards
    │   ├── charts.html      # Page displaying liquidity and volume charts
    │   ├── summary.html     # Page displaying a summary of token pair data
    │   ├── token_summary.html # Page displaying detailed token pair statistics
    │   └── ...
    ├── static/              # Directory for static files (e.g., CSS, JavaScript)
    │   ├── style.css        # Custom styles for the application
    │   └── ...
    ├── README.md            # Project documentation
    └── requirements.txt     # Python dependencies


## Installation

### Prerequisites

- Python 3.x
- Pip (Python package installer)

### Setup

1. **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/dexscreener-flask.git
    cd dexscreener-flask
    ```

2. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Run the application:**

    ```bash
    python app.py
    ```

4. **Open your browser and navigate to:**

    ```
    http://127.0.0.1:5000/
    ```

## Dependencies

- Flask
- Matplotlib
- Numpy
- Pandas
- Squarify
- Dexscreener
- Plotly

![image](https://github.com/user-attachments/assets/f6a694ee-0f54-484d-a507-6b8169ef1bef)
![image](https://github.com/user-attachments/assets/c351f74e-348a-419a-b54c-cbe600400fde)




