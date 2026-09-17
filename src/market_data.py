import json
import requests


def get_btc_price():

    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

    response = requests.get(url)

    data = response.json()

    price = float(data["price"])

    return price


def get_prices(asset_symbols):

    """
    قیمت لحظه‌ای چند دارایی رو در یک درخواست از بایننس می‌گیره.

    asset_symbols: دیکشنری مثل {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
    خروجی: دیکشنری مثل {"BTC": 65000.0, "ETH": 3200.0}
    """

    pairs = list(asset_symbols.values())

    url = "https://api.binance.com/api/v3/ticker/price"

    params = {
        "symbols": json.dumps(pairs)
    }

    response = requests.get(url, params=params)

    data = response.json()

    price_by_pair = {
        item["symbol"]: float(item["price"])
        for item in data
    }

    prices = {}

    for asset, pair in asset_symbols.items():
        prices[asset] = price_by_pair[pair]

    return prices
