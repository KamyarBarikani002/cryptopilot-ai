def simulate_dca(
    prices,
    monthly_amount,
    start_capital
):

    capital = start_capital
    holdings = 0


    for price in prices:

        if capital >= monthly_amount:

            buy_amount = monthly_amount

            holdings += buy_amount / price

            capital -= buy_amount


    final_value = holdings * prices[-1] + capital

    return final_value