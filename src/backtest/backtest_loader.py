from src.backtest.strategy_backtest import run_strategy_backtest
from src.performance.performance_loader import PerformanceLoader


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
            /
            initial_capital
        ) * 100


        performance = PerformanceLoader().analyze(
            result["trade_history"],
            result["equity_curve"]
        )


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

            "trade_history": result["trade_history"],

            "performance": performance

        }
