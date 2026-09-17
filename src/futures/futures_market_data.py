import json
import requests

from config.settings import FUTURES_BASE_URL


def get_top_symbols_by_volume(top_n, quote_asset="USDT"):

    """
    پرحجم‌ترین قراردادهای فیوچرز دائمی (Perpetual) بر اساس حجم معاملات ۲۴ ساعته.
    """

    url = FUTURES_BASE_URL + "/fapi/v1/ticker/24hr"

    response = requests.get(url)

    data = response.json()

    perpetual_pairs = [
        item
        for item in data
        if item["symbol"].endswith(quote_asset)
        and "_" not in item["symbol"]  # قراردادهای تحویلی/فصلی رو کنار می‌گذاریم
    ]

    perpetual_pairs.sort(
        key=lambda item: float(item["quoteVolume"]),
        reverse=True
    )

    return [
        item["symbol"]
        for item in perpetual_pairs[:top_n]
    ]


def get_futures_klines(symbol, interval, limit=100):

    url = FUTURES_BASE_URL + "/fapi/v1/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    response = requests.get(url, params=params)

    return response.json()


def get_futures_prices(symbols):

    """
    قیمت لحظه‌ای چند نماد فیوچرز؛ برای به‌روزرسانی سیگنال‌های باز استفاده می‌شود.
    """

    if not symbols:
        return {}

    url = FUTURES_BASE_URL + "/fapi/v1/ticker/price"

    params = {
        "symbols": json.dumps(list(symbols))
    }

    response = requests.get(url, params=params)

    data = response.json()

    return {
        item["symbol"]: float(item["price"])
        for item in data
    }
