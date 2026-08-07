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

    trade_history = []

    equity_curve = []


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
            "Price:",
            price,
            "| Regime:",
            regime,
            "| Score:",
            score,
            "| RSI:",
            round(rsi, 2),
            "| Decision:",
            decision
        )


        if (
            decision in ["BUY", "ACCUMULATE"]
            and capital > 0
        ):

            btc = capital / price

            capital = 0

            trades += 1


            trade_history.append(
                {
                    "type": "BUY",
                    "price": price,
                    "amount": btc
                }
            )


        elif (
            decision == "SELL"
            and btc > 0
        ):

            capital = btc * price

            profit = (
                capital
                - initial_capital
            )


            btc = 0

            trades += 1


            trade_history.append(
                {
                    "type": "SELL",
                    "price": price,
                    "profit": round(
                        profit,
                        2
                    )
                }
            )


        current_value = (
            capital
            +
            btc * price
        )


        equity_curve.append(
            current_value
        )


    final_value = (
        capital
        +
        btc * prices[-1]
    )


    return {

        "final_value": final_value,

        "trades": trades,

        "trade_history": trade_history,

        "equity_curve": equity_curve

    }
