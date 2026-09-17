from src.technical_analysis import calculate_ma, calculate_rsi
from src.market_regime import detect_market_regime
from src.portfolio.portfolio_loader import PortfolioLoader
from src.risk.risk_loader import RiskLoader


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


        current_value = 0


        if holdings:

            for asset in holdings:

                current_value += (
                    holdings[asset]
                    *
                    prices[asset][day]
                )

        else:

            current_value = capital


        capital = current_value


        # تغییر Regime
        if regime != current_regime:

            # Risk Engine
            risk = RiskLoader().analyze(
                capital,
                regime
            )


            # Portfolio Allocation
            portfolio = PortfolioLoader().create(
                capital,
                regime
            )


            # محدود کردن Exposure بر اساس Risk
            position_size = min(
                capital,
                risk["position_size"]
            )


            scale = 1

            if capital > 0:

                scale = (
                    position_size
                    /
                    capital
                )


            holdings = {}


            for asset, amount in portfolio.items():

                adjusted_amount = (
                    amount
                    *
                    scale
                )


                holdings[asset] = (
                    adjusted_amount
                    /
                    prices[asset][day]
                )


            # مقدار سرمایه خارج از پوزیشن
            invested = (
                sum(
                    holdings[asset]
                    *
                    prices[asset][day]
                    for asset in holdings
                )
            )


            capital = (
                capital
                -
                invested
            )


            current_regime = regime

            allocation_changes += 1


        # ارزش کل Portfolio
        value = capital


        for asset in holdings:

            value += (
                holdings[asset]
                *
                prices[asset][day]
            )


        equity_curve.append(
            value
        )


    # Final Portfolio Value

    if equity_curve:

        final_value = equity_curve[-1]

    else:

        final_value = initial_capital


    # Drawdown

    peak = 0

    max_drawdown = 0


    for value in equity_curve:

        if value > peak:

            peak = value


        if peak > 0:

            drawdown = (
                (peak - value)
                /
                peak
            ) * 100


            if drawdown > max_drawdown:

                max_drawdown = drawdown


    return {

        "initial_capital": initial_capital,

        "final_value": final_value,

        "equity_curve": equity_curve,

        "regime_history": regime_history,

        "allocation_changes": allocation_changes,

        "max_drawdown": round(
            max_drawdown,
            2
        )

    }
