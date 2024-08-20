#Dexscreener Flask Application
##Overview
This project is a Flask-based web application that integrates with the Dexscreener API to display cryptocurrency token pair details. The application generates dynamic HTML content to visualize token liquidity, prices, and volumes, providing a user-friendly interface for exploring token data.

##Features
Dynamic Token Pair Cards: Display token pair details including liquidity, price, and volume in an organized card format.
Interactive Summary Display: Click on a token pair card to display detailed information in a fixed summary div.
Charts Visualization: Generate pie and tree charts for liquidity and volume data using Matplotlib and Squarify.
Responsive Design: The layout adapts to different screen sizes, ensuring a consistent user experience across devices.

project-root/
│
├── app.py                # Main Flask application file
├── templates/            # HTML templates for the application
│   ├── base.html         # Base template for consistent layout
│   ├── index.html        # Main page displaying token pair cards
│   ├── charts.html       # Page displaying liquidity and volume charts
│   ├── summary.html      # Page displaying a summary of token pair data
│   ├── token_summary.html# Page displaying detailed token pair statistics
│   └── ...
├── static/               # Directory for static files (e.g., CSS, JavaScript)
│   ├── style.css         # Custom styles for the application
│   └── ...
├── README.md             # Project documentation
└── requirements.txt      # Python dependencies


![image](https://github.com/user-attachments/assets/3ee9b9a6-bf24-4075-8111-e42263f42ae7)

![image](https://github.com/user-attachments/assets/4f8102e3-3394-4786-bb9c-afdca85de3a0)

![image](https://github.com/user-attachments/assets/6203f77d-4b54-4a06-a7f4-bab6f7b4f345)


