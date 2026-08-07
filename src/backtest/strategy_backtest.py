from src.technical_analysis import calculate_ma, calculate_rsi
from src.scoring_engine import calculate_score
from src.strategy_engine import final_decision


def run_strategy_backtest(
    prices,
    initial_capital
):

    capital = initial_capital
    btc = 0
    trades = 0


    for i in range(20, len(prices)):

        history = prices[:i]

        ma = calculate_ma(history)

        rsi = calculate_rsi(history)


        score = calculate_score(
            prices[i],
            ma,
            rsi
        )


        decision = final_decision(
            "BULL",
            score,
            rsi
        )


        price = prices[i]


        print(
            "Price:",
            price,
            "| Score:",
            score,
            "| RSI:",
            round(rsi, 2),
            "| Decision:",
            decision
        )


        if decision in [
            "BUY",
            "ACCUMULATE"
        ] and capital > 0:

            btc += capital / price

            capital = 0

            trades += 1



    final_value = (
        btc * prices[-1]
        + capital
    )


    return {
        "final_value": final_value,
        "trades": trades
    }
