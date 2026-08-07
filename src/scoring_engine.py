def calculate_score(price, ma, rsi):

    score = 50

    # Trend
    if price > ma:
        score += 20
    else:
        score -= 20

    # RSI
    if rsi < 30:
        score += 20
    elif rsi > 70:
        score -= 10
    else:
        score += 10

    return max(0, min(score, 100))


def get_decision(score):

    if score >= 80:
        return "BUY"

    elif score <= 40:
        return "SELL"

    else:
        return "HOLD"