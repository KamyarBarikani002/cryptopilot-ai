from src.backtest.portfolio_loader import PortfolioBacktestLoader


prices = {

    "BTC": [
        60000,
        62000,
        65000,
        68000
    ],

    "ETH": [
        3000,
        3100,
        3200,
        3400
    ],

    "LINK": [
        20,
        22,
        25,
        28
    ],

    "ONDO": [
        1,
        1.2,
        1.5,
        1.8
    ],

    "NEAR": [
        5,
        5.5,
        6,
        7
    ]

}


engine = PortfolioBacktestLoader()


report = engine.run(
    prices,
    200,
    "BULL"
)


print("========================")
print("Portfolio Backtest")
print("========================")


print(
    "Initial Capital:",
    report["initial_capital"],
    "$"
)

print(
    "Final Value:",
    report["final_value"],
    "$"
)

print(
    "Profit:",
    report["profit"],
    "$"
)

print(
    "Return:",
    report["return_percent"],
    "%"
)


print(
    "Peak Equity:",
    report["peak_equity"],
    "$"
)

print(
    "Max Drawdown:",
    report["max_drawdown"],
    "%"
)


print()

print("========================")
print("Asset Performance")
print("========================")


for asset, performance in report["asset_performance"].items():

    print(
        asset,
        ":",
        performance,
        "%"
    )


print("========================")
