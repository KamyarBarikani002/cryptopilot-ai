import json

from config.settings import SPOT_BASE_URL
from src.binance_client import binance_get


def get_btc_price():

    data = binance_get(
        SPOT_BASE_URL + "/api/v3/ticker/price",
        params={"symbol": "BTCUSDT"}
    )

    return float(data["price"])


def get_prices(asset_symbols):

    """
    قیمت لحظه‌ای چند دارایی رو در یک درخواست از بایننس می‌گیره.

    asset_symbols: دیکشنری مثل {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
    خروجی: دیکشنری مثل {"BTC": 65000.0, "ETH": 3200.0}
    """

    pairs = list(asset_symbols.values())

    data = binance_get(
        SPOT_BASE_URL + "/api/v3/ticker/price",
        params={"symbols": json.dumps(pairs, separators=(",", ":"))}
    )

    price_by_pair = {
        item["symbol"]: float(item["price"])
        for item in data
    }

    prices = {}

    for asset, pair in asset_symbols.items():
        prices[asset] = price_by_pair[pair]

    return prices
