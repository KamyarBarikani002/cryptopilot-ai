def get_dca_triggers(price, ma, rsi):

    triggers = {}

    triggers["Entry 1"] = (
        "RSI oversold"
        if rsi < 25
        else "WAIT"
    )

    triggers["Entry 2"] = (
        "Buy on -5% drop"
    )

    triggers["Entry 3"] = (
        "RSI recovery above 35"
    )

    triggers["Entry 4"] = (
        "Price above MA20"
    )

    return triggers