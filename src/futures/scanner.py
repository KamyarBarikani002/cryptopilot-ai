"""
اسکنر فیوچرز: پرحجم‌ترین قراردادهای کوکوین را با استراتژی انتخاب‌شده در
config/settings.py (SIGNAL_STRATEGY، تعریف‌ها در src/futures/strategy.py)
بررسی می‌کند و برای هر فرصت یک پلن معامله با نسبت سود به ضرر دست‌کم ۱ به ۲
(بعد از کارمزد) می‌سازد.

فاندامنتال (فاندینگ، روند Open Interest، ترس‌وطمع) شرط ورود نیست (مگر فیلتر
فاندینگ در پارامترها روشن باشد)؛ فقط در امتیاز اطمینان و ترتیب نمایش اثر دارد.
"""

from concurrent.futures import ThreadPoolExecutor

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
    get_turnover_24h,
)
from src.futures.futures_risk import build_trade_plan
from src.news.feeds import build_news_context, macro_risk_now
from src.news.sentiment import normalize_coin


NEWS_BLOCK_SCORE = 3   # امتیاز خبری ۲۴ ساعت اخیر که از آن به بعد معامله‌ی خلاف‌جهت بسته می‌شود


def base_coin(symbol):

    """XBTUSDTM -> BTC ، SOLUSDTM -> SOL"""

    for suffix in ("USDTM", "USDCM", "USDM"):
        if symbol.endswith(suffix):
            return normalize_coin(symbol[: -len(suffix)])
    return normalize_coin(symbol)


def apply_news(opportunity, news, macro_event):

    """
    اثر خبرها روی یک فرصت:
    - ارزی که کوکوین اعلام حذفش را داده: مسدود
    - خبر اقتصادی مهم آمریکا در ۲ ساعت آینده یا ۱ ساعت گذشته: مسدود
    - خبرهای خیلی منفی (برای Long) یا خیلی مثبت (برای Short) در ۲۴ ساعت اخیر: مسدود
    - خبرهای کمتر شدید: اطمینان را کمی بالا/پایین می‌برند
    """

    coin = base_coin(opportunity["symbol"])
    sign = 1 if opportunity["direction"] == "LONG" else -1
    score = news.get("coin_scores", {}).get(coin, 0)

    opportunity["news_score"] = score
    opportunity["blocked_reason"] = None

    if coin in news.get("delisted_coins", set()):
        opportunity["blocked_reason"] = "کوکوین حذف این ارز را اعلام کرده"
    elif macro_event is not None:
        opportunity["blocked_reason"] = (
            "خبر مهم اقتصادی آمریکا: " + macro_event["title"] + " ("
            + macro_event["time"].strftime("%H:%M UTC") + ")"
        )
    elif score * sign <= -NEWS_BLOCK_SCORE:
        opportunity["blocked_reason"] = "خبرهای " + ("منفی" if sign == 1 else "مثبت") + " ۲۴ ساعت اخیر این ارز"

    adjustment = max(-10, min(10, 3 * score * sign))
    opportunity["confidence"] = max(0, min(100, opportunity["confidence"] + adjustment))
    opportunity["score"] = opportunity["confidence"] * sign

    return opportunity


SCAN_WORKERS = 8


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
    risk_percent=RISK_PER_TRADE_FUTURES,
    turnover_fetcher=get_turnover_24h,
):

    """یک فرصت (dict) یا None اگر الان شرایط ورود برقرار نیست."""

    needed = strategy.MIN_CANDLES_BY_STRATEGY[SIGNAL_STRATEGY]

    # فقط به اندازه‌ای که استراتژی لازم دارد (کوکوین هر بار ۲۰۰ کندل می‌دهد؛
    # برای ۵۰۰+ ارز هر درخواست اضافه یعنی اسکن کندتر)
    candles = kline_fetcher(symbol, SCAN_INTERVAL, min(SCAN_CANDLES, needed + 40))

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
        risk_percent,
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
        "reasons": signal.get("reasons", []),
    }
    opportunity.update(plan)
    opportunity["turnover_24h"] = _safe(turnover_fetcher, symbol, 0.0)

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
    risk_percent=None,
    turnover_fetcher=get_turnover_24h,
    news_fetcher=build_news_context,
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

    risk = risk_percent if risk_percent is not None else RISK_PER_TRADE_FUTURES

    def scan_one(symbol):
        try:
            return scan_symbol(
                symbol, capital, kline_fetcher, funding_fetcher, oi_fetcher,
                fear_greed_value, tick_size_fetcher, risk, turnover_fetcher,
            ), None
        except Exception as error:
            return None, {"symbol": symbol, "error": str(error)}

    # همه‌ی ارزهای کوکوین (۴۰۰+) یکی‌یکی چند دقیقه طول می‌کشید؛ چند تا همزمان
    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
        outcomes = list(pool.map(scan_one, symbols))

    opportunities = [o for o, _ in outcomes if o is not None]
    skipped = [e for _, e in outcomes if e is not None]

    try:
        news = news_fetcher()
    except Exception:
        news = {}
    macro_event = macro_risk_now(news) if news else None

    for opportunity in opportunities:
        apply_news(opportunity, news, macro_event)

    tradable = [o for o in opportunities if not o["blocked_reason"]]
    blocked = [o for o in opportunities if o["blocked_reason"]]

    longs = sorted([o for o in tradable if o["direction"] == "LONG"], key=lambda o: o["confidence"], reverse=True)
    shorts = sorted([o for o in tradable if o["direction"] == "SHORT"], key=lambda o: o["confidence"], reverse=True)

    return {
        "scanned": len(symbols),
        "longs": longs,
        "shorts": shorts,
        "blocked": blocked,
        "macro_event": macro_event,
        "news_errors": news.get("errors", []) if news else ["منابع خبری در دسترس نبودند"],
        "skipped": skipped,
        "fear_greed_index": fear_greed_value,
    }
