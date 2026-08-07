from src.technical_analysis import calculate_ma, calculate_rsi
from src.scoring_engine import calculate_score
from src.market_regime import detect_market_regime
from src.strategy_engine import final_decision
from src.risk.risk_loader import RiskLoader


def run_strategy_backtest(
    prices,
    initial_capital
):

    capital = initial_capital

    btc = 0

    trades = 0

    trade_history = []

    equity_curve = []

    entry_value = 0


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


        risk = RiskLoader().analyze(
            capital,
            regime
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


        # BUY فقط وقتی پوزیشن نداریم
        if (
            decision in ["BUY", "ACCUMULATE"]
            and capital > 0
            and btc == 0
        ):

            position_size = min(
                capital,
                risk["position_size"]
            )


            btc = position_size / price

            capital -= position_size

            entry_value = position_size

            trades += 1


            trade_history.append(
                {
                    "type": "BUY",
                    "price": price,
                    "amount": btc,
                    "size": position_size
                }
            )



        # SELL
        elif (
            decision == "SELL"
            and btc > 0
        ):

            sell_value = btc * price


            profit = (
                sell_value
                -
                entry_value
            )


            capital += sell_value

            btc = 0

            entry_value = 0

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


        equity_curve.append(
            capital
            +
            btc * price
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
