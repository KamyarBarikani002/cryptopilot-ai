"""
داده‌ی بازار فیوچرز (قراردادهای دائمی USDT) از کوکوین.

نکاتی که روی پاسخ زنده‌ی API کوکوین بررسی شد:
- اسم قراردادها فرق دارد: بیت‌کوین XBTUSDTM است، اتریوم ETHUSDTM.
- لیست قراردادها سهام آمریکا را هم دارد (مثل AAPLUSDTM با assetClass="STOCK")؛
  این‌ها فیلتر می‌شوند تا اسکنر سهام اپل را فرصت کریپتو معرفی نکند.
- کندل‌های فیوچرز از قدیم به جدید و با ترتیب [time_ms, open, high, low, close,
  volume, turnover] می‌آیند، که بر خلاف اسپات، همان ترتیب بایننس است.
- granularity بر حسب دقیقه است (60 = یک ساعت).
"""

import time

from config.settings import KUCOIN_FUTURES_URL
from src.exchange_client import ExchangeUnavailable, kucoin_get

# لیست قراردادها هم برای انتخاب ارزها و هم برای نرخ فاندینگ لازم است؛ با این کش
# یک اسکن کامل فقط یک بار این لیست را می‌گیرد، نه یک بار به‌ازای هر ارز.
_CONTRACTS_CACHE_SECONDS = 60
_contracts_cache = {"at": 0.0, "by_symbol": {}}

_GRANULARITY_MINUTES = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "2h": 120, "4h": 240, "8h": 480,
    "12h": 720, "1d": 1440, "1w": 10080,
}


def get_active_contracts(max_age_seconds=_CONTRACTS_CACHE_SECONDS):

    """همه‌ی قراردادهای فعال کوکوین، به شکل {symbol: contract}."""

    now = time.time()

    if _contracts_cache["by_symbol"] and now - _contracts_cache["at"] < max_age_seconds:
        return _contracts_cache["by_symbol"]

    data = kucoin_get(KUCOIN_FUTURES_URL + "/api/v1/contracts/active")

    if not data:
        raise ExchangeUnavailable("کوکوین لیست قراردادهای فیوچرز را برنگرداند.")

    by_symbol = {contract["symbol"]: contract for contract in data}

    _contracts_cache["at"] = now
    _contracts_cache["by_symbol"] = by_symbol

    return by_symbol


def is_scannable_contract(contract, quote_asset="USDT"):

    """فقط قراردادهای دائمی، خطی، کریپتویی و در حال معامله‌ی عادی."""

    return (
        contract.get("quoteCurrency") == quote_asset
        and not contract.get("isInverse")
        and contract.get("status") == "Open"
        and contract.get("expireDate") is None
        and contract.get("assetClass", "CRYPTO") == "CRYPTO"
        and contract.get("marketStage", "NORMAL") == "NORMAL"
    )


def get_top_symbols_by_volume(top_n, quote_asset="USDT"):

    """
    پرحجم‌ترین قراردادهای فیوچرز دائمی بر اساس گردش معاملات ۲۴ ساعته (به دلار).
    """

    contracts = get_active_contracts(max_age_seconds=0)

    eligible = [
        contract
        for contract in contracts.values()
        if is_scannable_contract(contract, quote_asset)
    ]

    eligible.sort(
        key=lambda contract: float(contract.get("turnoverOf24h") or 0),
        reverse=True
    )

    return [contract["symbol"] for contract in eligible[:top_n]]


def get_futures_klines(symbol, interval, limit=100):

    """کندل‌ها به شکل استاندارد [time_ms, open, high, low, close, volume]، قدیم به جدید."""

    granularity = _GRANULARITY_MINUTES[interval]
    now_ms = int(time.time() * 1000)
    from_ms = now_ms - granularity * 60_000 * (limit + 1)

    rows = kucoin_get(
        KUCOIN_FUTURES_URL + "/api/v1/kline/query",
        params={
            "symbol": symbol,
            "granularity": granularity,
            "from": from_ms,
            "to": now_ms
        }
    )

    if not rows:
        return []

    candles = [
        [int(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])]
        for row in rows
    ]

    candles.sort(key=lambda candle: candle[0])

    return candles[-limit:]


def get_futures_prices(symbols):

    """
    قیمت آخرین معامله‌ی چند قرارداد، برای به‌روزرسانی سیگنال‌های باز.
    نمادی که دیگر در کوکوین نیست (یا مال داده‌ی قدیمی بایننس است) کنار گذاشته می‌شود.
    """

    if not symbols:
        return {}

    contracts = get_active_contracts(max_age_seconds=0)

    prices = {}

    for symbol in symbols:

        contract = contracts.get(symbol)

        if contract and contract.get("lastTradePrice") is not None:
            prices[symbol] = float(contract["lastTradePrice"])

    return prices
