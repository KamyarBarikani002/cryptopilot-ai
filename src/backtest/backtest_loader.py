from src.backtest.strategy_backtest import run_strategy_backtest


class BacktestLoader:

    def run(
        self,
        prices,
        initial_capital
    ):

        result = run_strategy_backtest(
            prices,
            initial_capital
        )


        profit = (
            result["final_value"]
            - initial_capital
        )


        roi = (
            profit
            / initial_capital
        ) * 100


        return {

            "initial_capital": round(
                initial_capital,
                2
            ),

            "final_capital": round(
                result["final_value"],
                2
            ),

            "profit": round(
                profit,
                2
            ),

            "return_percent": round(
                roi,
                2
            ),

            "trades": result["trades"],

            "trade_history": result["trade_history"]

        }
