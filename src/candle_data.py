import requests


def get_btc_candles():

    url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol": "BTCUSDT",
        "interval": "1h",
        "limit": 100
    }

    response = requests.get(url, params=params)

    return response.json()