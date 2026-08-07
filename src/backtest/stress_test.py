from src.backtest.dynamic_portfolio_backtest import run_dynamic_portfolio_backtest
from src.performance.regime_report import RegimeReport


def run_stress_test(
    prices,
    initial_capital
):

    result = run_dynamic_portfolio_backtest(
        prices,
        initial_capital
    )


    regime_report = RegimeReport().analyze(
        result["regime_history"]
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

        "initial": initial_capital,

        "final": round(
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

        "allocation_changes": result[
            "allocation_changes"
        ],

        "regime_report": regime_report

    }
