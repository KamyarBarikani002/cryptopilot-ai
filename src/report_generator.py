def generate_report(
    price,
    ma,
    rsi,
    score,
    decision
):

    if price > ma:
        trend = "BULLISH"
    else:
        trend = "BEARISH"


    if rsi < 30:
        condition = "OVERSOLD"
    elif rsi > 70:
        condition = "OVERBOUGHT"
    else:
        condition = "NORMAL"


    if score >= 80:
        confidence = "HIGH"
    elif score >= 60:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"


    print("========================")
    print("CryptoPilot AI Report")
    print("========================")

    print("Asset: BTC/USDT")
    print()
    print("Price:", round(price, 2))
    print("Trend:", trend)
    print("RSI:", round(rsi, 2))
    print("Condition:", condition)

    print()
    print("Score:", score, "/100")
    print("Confidence:", confidence)

    print()
    print("Decision:", decision)

    print("========================")