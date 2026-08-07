def add_monthly_capital(
    current_capital,
    monthly_amount
):

    new_capital = current_capital + monthly_amount

    return new_capital


def calculate_monthly_plan(
    monthly_amount,
    regime
):

    if regime == "ACCUMULATION_ZONE":

        return {
            "BTC": monthly_amount * 0.45,
            "ETH": monthly_amount * 0.25,
            "LINK": monthly_amount * 0.12,
            "ONDO": monthly_amount * 0.10,
            "NEAR": monthly_amount * 0.08
        }

    elif regime == "BULL":

        return {
            "BTC": monthly_amount * 0.30,
            "ETH": monthly_amount * 0.25,
            "LINK": monthly_amount * 0.20,
            "ONDO": monthly_amount * 0.15,
            "NEAR": monthly_amount * 0.10
        }

    else:

        return {
            "BTC": monthly_amount * 0.50,
            "ETH": monthly_amount * 0.30,
            "Cash": monthly_amount * 0.20
        }