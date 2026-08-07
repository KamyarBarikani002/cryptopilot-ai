from src.portfolio.portfolio_loader import PortfolioLoader


def run_portfolio_backtest(
    prices,
    initial_capital,
    regime
):

    loader = PortfolioLoader()


    portfolio = loader.create(
        initial_capital,
        regime
    )


    holdings = {}


    for asset, amount in portfolio.items():

        holdings[asset] = {
            "capital": amount,
            "amount": (
                amount
                /
                prices[asset][0]
            )
        }


    equity_curve = []


    asset_performance = {}


    days = len(
        prices[
            list(prices.keys())[0]
        ]
    )


    for day in range(days):

        total_value = 0


        for asset in holdings:

            value = (
                holdings[asset]["amount"]
                *
                prices[asset][day]
            )


            total_value += value


        equity_curve.append(
            total_value
        )



    for asset in holdings:

        start_price = prices[asset][0]

        end_price = prices[asset][-1]


        change = (
            (
                end_price
                -
                start_price
            )
            /
            start_price
        ) * 100


        asset_performance[asset] = round(
            change,
            2
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

        "initial_capital": initial_capital,

        "final_value": equity_curve[-1],

        "equity_curve": equity_curve,

        "portfolio": portfolio,

        "asset_performance": asset_performance,

        "peak_equity": peak,

        "max_drawdown": round(
            max_drawdown,
            2
        )

    }
