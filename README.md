# Dexscreener Flask Application

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

Often it is beneficial to include some reference data into the project, such as
Rich Text Format (RTF) documentation, which is usually stored into the `docs`
or, less commonly, into the `doc` folder.

    .
    ├── ...
    ├── docs                    # Documentation files (alternatively `doc`)
    │   ├── TOC.md              # Table of contents
    │   ├── faq.md              # Frequently asked questions
    │   ├── misc.md             # Miscellaneous information
    │   ├── usage.md            # Getting started guide
    │   └── ...                 # etc.
    └── ...


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

## Usage

- **Homepage:** Displays token pair cards with basic information like chain ID, liquidity, price, and volume.
- **Click a Card:** Opens a detailed summary with more information and an interactive chart for the selected token pair.
- **Charts Page:** Provides visual insights into the liquidity and volume data of token pairs.

## Customization

### API Integration

The application integrates with the Dexscreener API using the `dexscreener` Python package. You can customize the token pairs displayed by modifying the `searchTicker` parameter in the `index()` function in `app.py`.

### Styling

The application uses custom CSS for styling. You can modify `style.css` located in the `static` directory to change the look and feel of the application.

### Chart Visualization

The charts are generated using Matplotlib and Squarify. You can modify the functions `tree_chart_liquidity`, `pie_chart_liquidity`, `tree_chart_volume`, and `pie_chart_volume` in `app.py` to customize the chart appearance.

## Dependencies

- Flask
- Matplotlib
- Numpy
- Pandas
- Squarify
- Dexscreener
- Plotly

## Contributing

Feel free to fork this repository, create a new branch, and submit a pull request with any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.



![image](https://github.com/user-attachments/assets/3ee9b9a6-bf24-4075-8111-e42263f42ae7)

![image](https://github.com/user-attachments/assets/4f8102e3-3394-4786-bb9c-afdca85de3a0)

![image](https://github.com/user-attachments/assets/6203f77d-4b54-4a06-a7f4-bab6f7b4f345)


