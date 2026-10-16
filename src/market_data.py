from config.settings import DEFAULT_SYMBOL, KUCOIN_SPOT_URL
from src.exchange_client import ExchangeUnavailable, kucoin_get


def get_spot_price(symbol):

    """قیمت آخرین معامله‌ی یک نماد اسپات کوکوین، مثل "BTC-USDT"."""

    data = kucoin_get(
        KUCOIN_SPOT_URL + "/api/v1/market/orderbook/level1",
        params={"symbol": symbol}
    )

    # برای نماد نامعتبر، کوکوین "data": null برمی‌گرداند نه خطا
    if not data or data.get("price") is None:
        raise ExchangeUnavailable("نماد " + symbol + " در بازار اسپات کوکوین پیدا نشد.")

    return float(data["price"])


def get_btc_price():

    return get_spot_price(DEFAULT_SYMBOL)


def get_prices(asset_symbols):

    """
    قیمت لحظه‌ای چند دارایی از اسپات کوکوین.

    asset_symbols: دیکشنری مثل {"BTC": "BTC-USDT", "ETH": "ETH-USDT"}
    خروجی: دیکشنری مثل {"BTC": 65000.0, "ETH": 3200.0}
    """

    return {
        asset: get_spot_price(pair)
        for asset, pair in asset_symbols.items()
    }
