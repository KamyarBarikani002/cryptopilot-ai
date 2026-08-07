import requests


def get_btc_price():

    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

    response = requests.get(url)

    data = response.json()

    price = float(data["price"])

    return price
