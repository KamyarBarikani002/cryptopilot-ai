from config.settings import (
    INITIAL_CAPITAL,
    SCAN_TOP_N,
    SCAN_INTERVAL,
    RISK_PER_TRADE_FUTURES,
    MAX_LEVERAGE,
    REWARD_RISK_RATIO,
    LONG_SCORE_THRESHOLD,
    SHORT_SCORE_THRESHOLD,
    TECHNICAL_WEIGHT,
    FUNDAMENTAL_WEIGHT
)
from src.futures.futures_market_data import get_top_symbols_by_volume, get_futures_klines
from src.futures.opportunity_engine import analyze_symbol, extract_closes, classify_opportunity
from src.futures.futures_risk import (
    estimate_volatility_percent,
    suggest_stop_loss_percent,
    calculate_futures_trade_plan
)
from src.futures.fundamental_engine import (
    get_funding_rate,
    get_open_interest_trend,
    get_fear_greed_index,
    calculate_fundamental_score
)


def scan_symbol(
    symbol,
    capital,
    kline_fetcher=get_futures_klines,
    funding_fetcher=get_funding_rate,
    oi_fetcher=get_open_interest_trend,
    fear_greed_value=50
):
    """
    یک ارز رو هم از نظر تکنیکال (روند + RSI) و هم از نظر فاندامنتال (فاندینگ،
    روند Open Interest، ترس‌وطمع کل بازار) بررسی می‌کند و این دو را در یک
    امتیاز نهایی (combined_score) ترکیب می‌کند؛ تصمیم Long/Short/None بر
    اساس همین امتیاز نهایی گرفته می‌شود، نه فقط تکنیکال.

    funding_fetcher و oi_fetcher قابل تزریق هستند (مثل symbol_fetcher/
    kline_fetcher در scan_market) تا هم تست/دموی بدون اتصال به بایننس ممکن
    باشد و هم رفتار پیش‌فرض (اتصال واقعی) دست‌نخورده بماند.
    """

    candles = kline_fetcher(symbol, SCAN_INTERVAL)

    result = analyze_symbol(symbol, candles)

    if result is None:
        return None

    closes = extract_closes(candles)

    price_trend_up = result["price"] > result["ma"]

    try:
        funding_rate_percent = funding_fetcher(symbol)
    except Exception:
        funding_rate_percent = 0.0

    try:
        oi_trend_percent = oi_fetcher(symbol)
    except Exception:
        oi_trend_percent = 0.0

    fundamental_score = calculate_fundamental_score(
        funding_rate_percent,
        oi_trend_percent,
        fear_greed_value,
        price_trend_up
    )

    combined_score = round(
        TECHNICAL_WEIGHT * result["technical_score"]
        + FUNDAMENTAL_WEIGHT * fundamental_score
    )

    direction = classify_opportunity(
        combined_score,
        LONG_SCORE_THRESHOLD,
        SHORT_SCORE_THRESHOLD
    )

    if direction == "NONE":
        return None

    volatility_percent = estimate_volatility_percent(closes)
    stop_loss_percent = suggest_stop_loss_percent(volatility_percent)

    plan = calculate_futures_trade_plan(
        direction, result["price"], capital, stop_loss_percent,
        RISK_PER_TRADE_FUTURES, REWARD_RISK_RATIO, MAX_LEVERAGE
    )

    opportunity = {
        "symbol": symbol,
        "price": result["price"],
        "ma": result["ma"],
        "rsi": result["rsi"],
        "technical_score": result["technical_score"],
        "fundamental_score": fundamental_score,
        "funding_rate_percent": round(funding_rate_percent, 4),
        "oi_trend_percent": round(oi_trend_percent, 2),
        "fear_greed_index": fear_greed_value,
        "score": combined_score,
        "direction": direction
    }
    opportunity["volatility_percent"] = round(volatility_percent, 2)
    opportunity.update(plan)
    return opportunity


def scan_market(
    top_n=None,
    capital=None,
    symbol_fetcher=get_top_symbols_by_volume,
    kline_fetcher=get_futures_klines,
    funding_fetcher=get_funding_rate,
    oi_fetcher=get_open_interest_trend,
    fear_greed_fetcher=get_fear_greed_index
):
    """
    symbol_fetcher، kline_fetcher، funding_fetcher، oi_fetcher و
    fear_greed_fetcher همگی قابل تزریق هستند تا هم تست/دموی بدون اتصال به
    بایننس ممکن باشد و هم رفتار پیش‌فرض (اتصال واقعی) دست‌نخورده بماند.

    شاخص ترس‌وطمع فقط یک‌بار در کل اسکن گرفته می‌شود (نه به‌ازای هر ارز)،
    چون این شاخص مربوط به کل بازار است، نه یک ارز خاص.
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
                symbol, capital, kline_fetcher,
                funding_fetcher, oi_fetcher, fear_greed_value
            )
            if opportunity is not None:
                opportunities.append(opportunity)
        except Exception as error:
            skipped.append({"symbol": symbol, "error": str(error)})
    longs = sorted([o for o in opportunities if o["direction"] == "LONG"], key=lambda o: o["score"], reverse=True)
    shorts = sorted([o for o in opportunities if o["direction"] == "SHORT"], key=lambda o: o["score"])
    return {
        "scanned": len(symbols),
        "longs": longs,
        "shorts": shorts,
        "skipped": skipped,
        "fear_greed_index": fear_greed_value
    }
