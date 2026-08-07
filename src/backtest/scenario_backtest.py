from src.backtest.dynamic_portfolio_backtest import run_dynamic_portfolio_backtest


def run_scenario_backtest(
    scenarios,
    initial_capital
):

    results = {}


    for name, prices in scenarios.items():

        result = run_dynamic_portfolio_backtest(
            prices,
            initial_capital
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


        results[name] = {

            "final_value": round(
                result["final_value"],
                2
            ),

            "profit": round(
                profit,
                2
            ),

            "return": round(
                roi,
                2
            ),

            "drawdown": result[
                "max_drawdown"
            ],

            "regime_changes": result[
                "allocation_changes"
            ]

        }


    return results
