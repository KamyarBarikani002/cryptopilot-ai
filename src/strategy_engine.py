def final_decision(
    regime,
    score,
    rsi
):

    if regime == "ACCUMULATION_ZONE":

        if score >= 50:
            return "ACCUMULATE"

        return "WAIT"



    elif regime == "BULL":

        # خروج از اشباع شدید
        if rsi > 90:
            return "SELL"


        # ورود در روند مثبت
        if score >= 70 and rsi < 80:
            return "BUY"


        # خرید مرحله‌ای
        elif score >= 60:
            return "ACCUMULATE"


        else:
            return "HOLD"



    elif regime == "BEAR":

        if score < 40:
            return "WAIT"

        elif rsi > 70:
            return "SELL"

        else:
            return "HOLD"



    else:

        if rsi > 90:
            return "SELL"

        elif score >= 65:
            return "ACCUMULATE"

        return "HOLD"
