"""
کندل‌های بازار اسپات کوکوین.

خروجی به همان شکلی است که بقیه‌ی کد (از زمان بایننس) انتظار دارد:
لیستی از [زمان شروع به میلی‌ثانیه، open، high، low، close، volume]، از قدیمی
به جدید. یعنی close همیشه در اندیس ۴ است.

کوکوین اسپات دو تفاوت دارد که اینجا جبران می‌شوند (روی پاسخ زنده بررسی شد):
- ترتیب فیلدها [time, open, CLOSE, HIGH, LOW, volume, turnover] است
- کندل‌ها از جدید به قدیم برمی‌گردند و زمان به ثانیه است
"""

import time

from config.settings import DEFAULT_INTERVAL, DEFAULT_SYMBOL, KUCOIN_SPOT_URL
from src.exchange_client import ExchangeUnavailable, kucoin_get

_SPOT_TYPES = {
    "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1hour", "2h": "2hour", "4h": "4hour", "6h": "6hour",
    "8h": "8hour", "12h": "12hour", "1d": "1day", "1w": "1week",
}

_INTERVAL_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600,
    "8h": 28800, "12h": 43200, "1d": 86400, "1w": 604800,
}


def normalize_spot_candles(rows):

    """[time_s, open, close, high, low, volume, ...] جدید-به-قدیم ← شکل استاندارد قدیم-به-جدید."""

    candles = [
        [int(row[0]) * 1000, float(row[1]), float(row[3]), float(row[4]), float(row[2]), float(row[5])]
        for row in rows
    ]

    candles.sort(key=lambda candle: candle[0])

    return candles


def get_spot_candles(symbol, interval="1h", limit=100):

    seconds = _INTERVAL_SECONDS[interval]
    end_at = int(time.time())
    start_at = end_at - seconds * (limit + 1)

    rows = kucoin_get(
        KUCOIN_SPOT_URL + "/api/v1/market/candles",
        params={
            "symbol": symbol,
            "type": _SPOT_TYPES[interval],
            "startAt": start_at,
            "endAt": end_at
        }
    )

    if not rows:
        raise ExchangeUnavailable("کوکوین برای " + symbol + " کندلی برنگرداند.")

    return normalize_spot_candles(rows)[-limit:]


def get_btc_candles():

    return get_spot_candles(DEFAULT_SYMBOL, DEFAULT_INTERVAL, 100)
