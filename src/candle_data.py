from config.settings import SPOT_BASE_URL
from src.binance_client import binance_get


def get_btc_candles():

    return binance_get(
        SPOT_BASE_URL + "/api/v3/klines",
        params={
            "symbol": "BTCUSDT",
            "interval": "1h",
            "limit": 100
        }
    )
