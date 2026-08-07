from src.technical_analysis import calculate_ma, calculate_rsi
from src.market_regime import detect_market_regime
from src.portfolio.portfolio_loader import PortfolioLoader


def run_dynamic_portfolio_backtest(
    prices,
    initial_capital
):

    capital = initial_capital

    holdings = {}

    equity_curve = []

    regime_history = []

    allocation_changes = 0


    assets = list(prices.keys())


    days = len(
        prices[assets[0]]
    )


    current_regime = None



    for day in range(20, days):

        total_prices = []


        for asset in assets:

            total_prices.append(
                prices[asset][day]
            )


        btc_history = prices["BTC"][:day]


        ma = calculate_ma(
            btc_history
        )

        rsi = calculate_rsi(
            btc_history
        )


        regime = detect_market_regime(
            prices["BTC"][day],
            ma,
            rsi
        )


        regime_history.append(
            regime
        )


        if regime != current_regime:

            portfolio = PortfolioLoader().create(
                capital,
                regime
            )

            holdings = {}


            for asset, amount in portfolio.items():

                holdings[asset] = (
                    amount
                    /
                    prices[asset][day]
                )


            current_regime = regime

            allocation_changes += 1



        value = 0


        for asset in holdings:

            value += (
                holdings[asset]
                *
                prices[asset][day]
            )


        equity_curve.append(
            value
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

        "regime_history": regime_history,

        "allocation_changes": allocation_changes,

        "max_drawdown": round(
            max_drawdown,
            2
        )

    }
