def final_decision(regime, score):

    if regime == "ACCUMULATION_ZONE" and score >= 50:
        return "ACCUMULATE"

    elif regime == "BULL" and score >= 70:
        return "BUY"

    elif regime == "BEAR" and score < 40:
        return "WAIT"

    else:
        return "HOLD"