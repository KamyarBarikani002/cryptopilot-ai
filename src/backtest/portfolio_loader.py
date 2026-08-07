from src.backtest.portfolio_backtest import run_portfolio_backtest


class PortfolioBacktestLoader:


    def run(
        self,
        prices,
        initial_capital,
        regime
    ):

        result = run_portfolio_backtest(
            prices,
            initial_capital,
            regime
        )


        profit = (
            result["final_value"]
            -
            initial_capital
        )


        roi = (
            profit
            /
            initial_capital
        ) * 100



        return {

            "initial_capital": round(
                initial_capital,
                2
            ),

            "final_value": round(
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

            "peak_equity": round(
                result["peak_equity"],
                2
            ),

            "max_drawdown": result["max_drawdown"],

            "asset_performance": result["asset_performance"],

            "portfolio": result["portfolio"]

        }
