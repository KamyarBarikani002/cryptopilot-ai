def create_dynamic_portfolio(capital, regime):

    if regime == "BULL":

        allocation = {
            "BTC": 0.30,
            "ETH": 0.25,
            "LINK": 0.20,
            "ONDO": 0.15,
            "NEAR": 0.10
        }


    elif regime == "ACCUMULATION_ZONE":

        allocation = {
            "BTC": 0.45,
            "ETH": 0.25,
            "LINK": 0.12,
            "ONDO": 0.10,
            "NEAR": 0.08
        }


    elif regime == "BEAR":

        allocation = {
            "BTC": 0.60,
            "ETH": 0.20,
            "LINK": 0.10,
            "ONDO": 0.05,
            "NEAR": 0.05
        }


    else:

        allocation = {
            "BTC": 0.50,
            "ETH": 0.25,
            "LINK": 0.10,
            "ONDO": 0.10,
            "NEAR": 0.05
        }


    portfolio = {}

    for coin, percentage in allocation.items():
        portfolio[coin] = capital * percentage


    return portfolio