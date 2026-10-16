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
    top_n = None یا 0 یعنی همه‌ی قراردادهای قابل اسکن کوکوین.
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

    if top_n:
        eligible = eligible[:top_n]

    return [contract["symbol"] for contract in eligible]


def get_turnover_24h(symbol):

    """گردش معاملات ۲۴ ساعته‌ی قرارداد به دلار (برای تشخیص ارزهای کم‌حجم)."""

    contract = get_active_contracts().get(symbol) or {}

    return float(contract.get("turnoverOf24h") or 0)


# کوکوین در هر درخواست کندل فیوچرز حداکثر ۲۰۰ کندل برمی‌گرداند (نه ۵۰۰).
# بازه‌های بلندتر باید تکه‌تکه گرفته شوند، وگرنه وسط داده جای خالی می‌افتد.
KUCOIN_MAX_KLINES = 200
KLINE_PAGE_CANDLES = 190


def get_futures_klines(symbol, interval, limit=100, closed_only=False):

    """کندل‌ها به شکل استاندارد [time_ms, open, high, low, close, volume]، قدیم به جدید."""

    granularity = _GRANULARITY_MINUTES[interval]
    now_ms = int(time.time() * 1000)
    from_ms = now_ms - granularity * 60_000 * (limit + 1)

    if limit + 1 > KLINE_PAGE_CANDLES:
        # بیشتر از سقف یک درخواست: چند تکه
        candles = get_futures_klines_range(symbol, interval, from_ms, now_ms, pause_seconds=0)
        return candles[-limit:]

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

    if closed_only:
        # کندل آخر کوکوین معمولاً هنوز در حال شکل گرفتن است؛ تحلیل فقط روی
        # کندل‌های بسته‌شده انجام می‌شود تا سیگنال وسط کندل عوض نشود.
        step_ms = granularity * 60_000
        candles = [c for c in candles if c[0] + step_ms <= now_ms]

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


def get_tick_size(symbol):

    """گام قیمت قرارداد (مثلاً 0.1 برای بیت‌کوین، 1e-10 برای PEPE)، یا None."""

    try:
        contract = get_active_contracts().get(symbol)
    except ExchangeUnavailable:
        return None

    if not contract or contract.get("tickSize") in (None, 0):
        return None

    return float(contract["tickSize"])


def _missing_candles(times, step_ms):

    """تعداد کندل‌هایی که بین اولین و آخرین کندل جا افتاده‌اند."""

    if len(times) < 2:
        return 0

    expected = (times[-1] - times[0]) // step_ms + 1

    return int(expected - len(times))


def get_futures_klines_range(symbol, interval, start_ms, end_ms, pause_seconds=0.1, attempts=3):

    """
    کندل‌های یک بازه‌ی طولانی (برای بک‌تست)؛ چون کوکوین حداکثر ۵۰۰ کندل در هر
    درخواست می‌دهد، بازه تکه‌تکه گرفته می‌شود. فقط کندل‌های بسته‌شده برمی‌گردند.

    زیر فشار (وقتی چند ارز همزمان دانلود می‌شوند) کوکوین گاهی یک تکه را خالی
    برمی‌گرداند؛ آن‌وقت وسط داده جای خالی می‌افتد و اندیکاتورها غلط می‌شوند.
    برای همین تکه‌ی خالیِ وسط داده دوباره گرفته می‌شود، و اگر آخر کار هنوز
    بیش از ۱٪ کندل‌ها کم باشد، خطا داده می‌شود تا این ارز در نتیجه حساب نشود.
    """

    granularity = _GRANULARITY_MINUTES[interval]
    step_ms = granularity * 60_000
    page_ms = step_ms * KLINE_PAGE_CANDLES
    rows = {}
    cursor = start_ms

    while cursor < end_ms:

        to_ms = min(cursor + page_ms, end_ms)

        for attempt in range(attempts):

            data = kucoin_get(
                KUCOIN_FUTURES_URL + "/api/v1/kline/query",
                params={"symbol": symbol, "granularity": granularity, "from": cursor, "to": to_ms},
            ) or []

            # تکه‌ی خالی قبل از لیست شدن ارز طبیعی است؛ بعد از آن نه
            if data or not rows:
                break

            time.sleep(1 + attempt)

        for row in data:
            rows[int(row[0])] = [int(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])]

        cursor = to_ms
        if pause_seconds:
            time.sleep(pause_seconds)

    now_ms = int(time.time() * 1000)
    candles = [rows[t] for t in sorted(rows) if t + step_ms <= now_ms]

    missing = _missing_candles([c[0] for c in candles], step_ms)
    if candles and missing > 0.01 * (len(candles) + missing):
        raise ExchangeUnavailable(
            "داده‌ی " + symbol + " ناقص است (" + str(missing) + " کندل جا افتاده)؛ در بک‌تست حساب نشد."
        )

    return candles
