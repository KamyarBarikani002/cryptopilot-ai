from src.backtest.dynamic_portfolio_backtest import run_dynamic_portfolio_backtest


prices = {

    "BTC": [
        60000,
        61000,
        62000,
        63000,
        64000,
        65000,
        66000,
        68000,
        70000,
        72000,
        74000,
        76000,
        78000,
        80000,
        82000,
        84000,
        86000,
        88000,
        90000,
        92000,
        95000,
        98000
    ],

    "ETH": [
        3000,
        3050,
        3100,
        3200,
        3300,
        3400,
        3500,
        3600,
        3700,
        3800,
        3900,
        4000,
        4100,
        4200,
        4300,
        4400,
        4500,
        4600,
        4700,
        4800,
        4900,
        5000
    ],

    "LINK": [
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
        40,
        42
    ],

    "ONDO": [
        1,
        1.05,
        1.1,
        1.15,
        1.2,
        1.25,
        1.3,
        1.35,
        1.4,
        1.45,
        1.5,
        1.55,
        1.6,
        1.65,
        1.7,
        1.75,
        1.8,
        1.85,
        1.9,
        1.95,
        2,
        2.1
    ],

    "NEAR": [
        5,
        5.1,
        5.2,
        5.3,
        5.4,
        5.5,
        5.6,
        5.8,
        6,
        6.2,
        6.4,
        6.6,
        6.8,
        7,
        7.2,
        7.4,
        7.6,
        7.8,
        8,
        8.2,
        8.5,
        9
    ]

}


result = run_dynamic_portfolio_backtest(
    prices,
    200
)


print("========================")
print("Dynamic Portfolio Backtest")
print("========================")


print(
    "Initial:",
    result["initial_capital"],
    "$"
)


print(
    "Final:",
    round(
        result["final_value"],
        2
    ),
    "$"
)


print(
    "Allocation Changes:",
    result["allocation_changes"]
)


print(
    "Max Drawdown:",
    result["max_drawdown"],
    "%"
)


print("========================")
