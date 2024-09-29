def get_price_change_style(price_change):
    if price_change > 0:
        return "color: green;"
    elif price_change < 0:
        return "color: red;"
    else:
        return "color: gray;"

def format_price_change(price_change):
    return f"{price_change:.2f}%"
