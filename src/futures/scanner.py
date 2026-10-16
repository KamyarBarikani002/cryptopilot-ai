"""
اسکنر فیوچرز: پرحجم‌ترین قراردادهای کوکوین را با استراتژی انتخاب‌شده در
config/settings.py (SIGNAL_STRATEGY، تعریف‌ها در src/futures/strategy.py)
بررسی می‌کند و برای هر فرصت یک پلن معامله با نسبت سود به ضرر دست‌کم ۱ به ۲
(بعد از کارمزد) می‌سازد.

فاندامنتال (فاندینگ، روند Open Interest، ترس‌وطمع) شرط ورود نیست (مگر فیلتر
فاندینگ در پارامترها روشن باشد)؛ فقط در امتیاز اطمینان و ترتیب نمایش اثر دارد.
"""

from config.settings import (
    FUTURES_TAKER_FEE_PERCENT,
    INITIAL_CAPITAL,
    MAX_LEVERAGE,
    REWARD_RISK_RATIO,
    RISK_PER_TRADE_FUTURES,
    SCAN_CANDLES,
    SCAN_INTERVAL,
    SCAN_TOP_N,
    SIGNAL_STRATEGY,
    SIGNAL_STRATEGY_PARAMS,
)
from src.futures import strategy
from src.futures.fundamental_engine import (
    calculate_fundamental_score,
    get_fear_greed_index,
    get_funding_rate,
    get_open_interest_trend,
)
from src.futures.futures_market_data import (
    get_futures_klines,
    get_tick_size,
    get_top_symbols_by_volume,
)
from src.futures.futures_risk import build_trade_plan


def closed_futures_klines(symbol, interval, limit):

    return get_futures_klines(symbol, interval, limit, closed_only=True)


def _safe(fetch, symbol, default):

    try:
        return fetch(symbol)
    except Exception:
        return default


def scan_symbol(
    symbol,
    capital,
    kline_fetcher=closed_futures_klines,
    funding_fetcher=get_funding_rate,
    oi_fetcher=get_open_interest_trend,
    fear_greed_value=50,
    tick_size_fetcher=get_tick_size,
):

    """یک فرصت (dict) یا None اگر الان شرایط ورود برقرار نیست."""

    candles = kline_fetcher(symbol, SCAN_INTERVAL, SCAN_CANDLES)

    needed = strategy.MIN_CANDLES_BY_STRATEGY[SIGNAL_STRATEGY]

    if len(candles) < needed:
        raise ValueError(
            "فقط " + str(len(candles)) + " کندل موجود است؛ دست‌کم "
            + str(needed) + " لازم است (احتمالاً ارز تازه لیست شده)."
        )

    funding_rate_percent = _safe(funding_fetcher, symbol, None)

    signal = strategy.latest_signal(
        candles, funding_rate_percent, SIGNAL_STRATEGY_PARAMS, SIGNAL_STRATEGY
    )

    if signal is None:
        return None

    direction = signal["direction"]
    sign = 1 if direction == "LONG" else -1

    # Open Interest فقط برای ارزهایی که سیگنال دارند گرفته می‌شود (درخواست کمتر)
    oi_trend_percent = _safe(oi_fetcher, symbol, 0.0)

    fundamental_score = calculate_fundamental_score(
        funding_rate_percent or 0.0, oi_trend_percent, fear_greed_value, direction == "LONG"
    )

    # اطمینان ۰ تا ۱۰۰: ۷۵٪ کیفیت ستاپ تکنیکال + ۲۵٪ هم‌جهتی فاندامنتال
    fundamental_alignment = (fundamental_score * sign + 100) / 2
    confidence = round(0.75 * signal["strength"] + 0.25 * fundamental_alignment)

    plan = build_trade_plan(
        direction,
        signal["entry"],
        signal["stop"],
        capital,
        RISK_PER_TRADE_FUTURES,
        MAX_LEVERAGE,
        min_reward_risk=REWARD_RISK_RATIO,
        fee_percent=FUTURES_TAKER_FEE_PERCENT,
        tick_size=_safe(tick_size_fetcher, symbol, None),
    )

    opportunity = {
        "symbol": symbol,
        "direction": direction,
        "price": signal["entry"],
        "score": confidence * sign,
        "confidence": confidence,
        "technical_score": signal["strength"],
        "fundamental_score": fundamental_score,
        "funding_rate_percent": round(funding_rate_percent, 4) if funding_rate_percent is not None else None,
        "oi_trend_percent": round(oi_trend_percent, 2),
        "fear_greed_index": fear_greed_value,
        "rsi": signal["rsi"],
        "adx": signal["adx"],
        "volatility_percent": signal["atr_percent"],
    }
    opportunity.update(plan)

    return opportunity


def scan_market(
    top_n=None,
    capital=None,
    symbol_fetcher=get_top_symbols_by_volume,
    kline_fetcher=closed_futures_klines,
    funding_fetcher=get_funding_rate,
    oi_fetcher=get_open_interest_trend,
    fear_greed_fetcher=get_fear_greed_index,
    tick_size_fetcher=get_tick_size,
):
    """
    همه‌ی fetcher ها قابل تزریق‌اند تا تست و حالت آزمایشی بدون اتصال به کوکوین
    کار کنند. شاخص ترس‌وطمع فقط یک‌بار در کل اسکن گرفته می‌شود.
    """

    top_n = top_n if top_n is not None else SCAN_TOP_N
    capital = capital if capital is not None else INITIAL_CAPITAL
    symbols = symbol_fetcher(top_n)

    try:
        fear_greed_value = fear_greed_fetcher()
    except Exception:
        fear_greed_value = 50  # مقدار خنثی در صورت عدم دسترسی به این سرویس

    opportunities = []
    skipped = []

    for symbol in symbols:
        try:
            opportunity = scan_symbol(
                symbol, capital, kline_fetcher, funding_fetcher, oi_fetcher,
                fear_greed_value, tick_size_fetcher,
            )
            if opportunity is not None:
                opportunities.append(opportunity)
        except Exception as error:
            skipped.append({"symbol": symbol, "error": str(error)})

    longs = sorted([o for o in opportunities if o["direction"] == "LONG"], key=lambda o: o["confidence"], reverse=True)
    shorts = sorted([o for o in opportunities if o["direction"] == "SHORT"], key=lambda o: o["confidence"], reverse=True)

    return {
        "scanned": len(symbols),
        "longs": longs,
        "shorts": shorts,
        "skipped": skipped,
        "fear_greed_index": fear_greed_value,
    }
