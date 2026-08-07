class PerformanceLoader:


    def analyze(
        self,
        trade_history
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

        if total_trades > 0:

            win_rate = (
                len(winning)
                /
                total_trades
            ) * 100


        average_profit = 0

        if total_trades > 0:

            average_profit = (
                sum(profits)
                /
                total_trades
            )


        best_trade = 0

        if profits:

            best_trade = max(
                profits
            )


        worst_trade = 0

        if profits:

            worst_trade = min(
                profits
            )


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
                best_trade,
                2
            ),

            "worst_trade": round(
                worst_trade,
                2
            )

        }
