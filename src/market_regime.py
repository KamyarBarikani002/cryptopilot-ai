def detect_market_regime(price, ma, rsi):

    if price > ma and rsi > 55:
        return "BULL"

    elif price < ma and rsi < 25:
        return "ACCUMULATION_ZONE"

    elif price < ma and rsi < 45:
        return "BEAR"

    else:
        return "NEUTRAL"