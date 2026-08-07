def calculate_risk(
    capital,
    regime
):

    if regime == "BULL":

        risk_percent = 2
        stop_loss_percent = 5


    elif regime == "BEAR":

        risk_percent = 0.5
        stop_loss_percent = 2


    elif regime == "ACCUMULATION_ZONE":

        risk_percent = 1.5
        stop_loss_percent = 4


    else:

        risk_percent = 1
        stop_loss_percent = 3



    risk_amount = (
        capital
        *
        risk_percent
        /
        100
    )


    position_size = (
        risk_amount
        /
        (stop_loss_percent / 100)
    )


    take_profit_percent = (
        stop_loss_percent
        *
        3
    )


    return {

        "risk_percent": risk_percent,

        "risk_amount": round(
            risk_amount,
            2
        ),

        "stop_loss_percent": stop_loss_percent,

        "position_size": round(
            position_size,
            2
        ),

        "take_profit_percent": take_profit_percent

    }
