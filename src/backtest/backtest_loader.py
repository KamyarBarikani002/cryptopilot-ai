from src.backtest_engine import simulate_dca


class BacktestLoader:

    def run(
        self,
        prices,
        monthly_amount,
        start_capital
    ):

        return simulate_dca(
            prices,
            monthly_amount,
            start_capital
        )
