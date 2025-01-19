# Arbscreener Flask Application

## Overview

This project is a Flask-based web application that integrates with the Dexscreener API to display cryptocurrency token pair details. The application generates dynamic HTML content to visualize token liquidity, prices, and volumes, providing a user-friendly interface for exploring token data.

## Features

- **Dynamic Token Pair Cards:** Display token pair details including liquidity, price, and volume in an organized card format.
- **Interactive Summary Display:** Click on a token pair card to display detailed information in a fixed summary div.
- **Charts Visualization:** Generate pie and tree charts for liquidity and volume data using Matplotlib and Squarify.
- **Responsive Design:** The layout adapts to different screen sizes, ensuring a consistent user experience across devices.

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
  
![image](https://github.com/user-attachments/assets/ddd975d6-6b0d-4049-87e2-e670713be36d)





