def create_portfolio(capital):

    allocation = {
        "BTC": 0.40,
        "ETH": 0.25,
        "LINK": 0.15,
        "ONDO": 0.10,
        "NEAR": 0.10
    }

    portfolio = {}

    for coin, percentage in allocation.items():
        portfolio[coin] = capital * percentage

    return portfolio