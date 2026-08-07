class PerformanceLoader:


    def analyze(
        self,
        trade_history,
        equity_curve
    ):

        profits = []


        for trade in trade_history:

            if trade["type"] == "SELL":

                profits.append(
                    trade.get(
                        "profit",
                        0
                    )
                )


        total_trades = len(profits)


        winning = [
            p for p in profits
            if p > 0
        ]


        losing = [
            p for p in profits
            if p <= 0
        ]


        win_rate = 0

        if total_trades:

            win_rate = (
                len(winning)
                /
                total_trades
            ) * 100


        average_profit = 0

        if total_trades:

            average_profit = (
                sum(profits)
                /
                total_trades
            )


        peak = 0

        max_drawdown = 0


        for value in equity_curve:

            if value > peak:

                peak = value


            drawdown = (
                (peak - value)
                /
                peak
            ) * 100


            if drawdown > max_drawdown:

                max_drawdown = drawdown



        return {

            "total_trades": total_trades,

            "winning_trades": len(winning),

            "losing_trades": len(losing),

            "win_rate": round(
                win_rate,
                2
            ),

            "average_profit": round(
                average_profit,
                2
            ),

            "best_trade": round(
                max(profits) if profits else 0,
                2
            ),

            "worst_trade": round(
                min(profits) if profits else 0,
                2
            ),

            "peak_equity": round(
                peak,
                2
            ),

            "max_drawdown": round(
                max_drawdown,
                2
            )

        }
