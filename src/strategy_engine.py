def final_decision(
    regime,
    score,
    rsi
):

    if regime == "ACCUMULATION_ZONE":

        if score >= 50:
            return "ACCUMULATE"

        else:
            return "WAIT"



    elif regime == "BULL":

        if score >= 80 and rsi < 70:
            return "BUY"

        elif score >= 60:
            return "ACCUMULATE"

        else:
            return "HOLD"



    elif regime == "BEAR":

        if score < 40:
            return "REDUCE"

        else:
            return "WAIT"



    else:

        return "HOLD"
