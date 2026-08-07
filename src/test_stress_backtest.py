from src.backtest.stress_test import run_stress_test



def build_market(btc):

    return {

        "BTC": btc,

        "ETH": [
            x * 0.05
            for x in btc
        ],

        "LINK": [
            x * 0.0003
            for x in btc
        ],

        "ONDO": [
            x * 0.00002
            for x in btc
        ],

        "NEAR": [
            x * 0.00008
            for x in btc
        ]

    }



prices = build_market(
    [

        60000,
        65000,
        70000,
        75000,
        80000,

        76000,
        70000,
        62000,
        55000,
        48000,

        50000,
        58000,
        68000,
        78000,
        90000,

        100000,
        110000,
        120000,
        130000,
        140000,

        130000,
        115000,
        95000,
        85000

    ]
)



result = run_stress_test(
    prices,
    200
)



print("========================")
print("Stress Test Report")
print("========================")


print(
    "Initial:",
    result["initial"],
    "$"
)


print(
    "Final:",
    result["final"],
    "$"
)


print(
    "Profit:",
    result["profit"],
    "$"
)


print(
    "Return:",
    result["return"],
    "%"
)


print(
    "Max Drawdown:",
    result["drawdown"],
    "%"
)


print(
    "Portfolio Rebalances:",
    result["allocation_changes"]
)



print()
print("========================")
print("Regime Report")
print("========================")


report = result["regime_report"]


print(
    "Days:",
    report["days"]
)


print(
    "Changes:",
    report["changes"]
)


print(
    "Dominant:",
    report["dominant"]
)


print("========================")
