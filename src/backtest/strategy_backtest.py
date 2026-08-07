from src.technical_analysis import calculate_ma, calculate_rsi
from src.scoring_engine import calculate_score
from src.market_regime import detect_market_regime
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

        price = prices[i]


        regime = detect_market_regime(
            price,
            ma,
            rsi
        )


        score = calculate_score(
            price,
            ma,
            rsi
        )


        decision = final_decision(
            regime,
            score,
            rsi
        )


        print(
            "Price:", price,
            "| Regime:", regime,
            "| Score:", score,
            "| RSI:", round(rsi, 2),
            "| Decision:", decision
        )


        if (
            decision in ["BUY", "ACCUMULATE"]
            and capital > 0
        ):

            btc += capital / price
            capital = 0
            trades += 1


    final_value = (
        btc * prices[-1]
        + capital
    )


    return {
        "final_value": round(final_value, 2),
        "trades": trades
    }
