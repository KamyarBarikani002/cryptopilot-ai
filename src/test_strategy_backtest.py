from src.backtest.strategy_backtest import run_strategy_backtest


prices = [
    60000,
    59000,
    58000,
    61000,
    64000,
    65000,
    67000,
    66000,
    68000,
    69000,
    70000,
    71000,
    72000,
    73000,
    74000,
    75000,
    76000,
    77000,
    78000,
    79000,
    80000,
    81000,
    82000
]


result = run_strategy_backtest(
    prices,
    200
)


print("================")
print("STRATEGY BACKTEST")
print("================")

print(
    "Final Value:",
    result["final_value"]
)

print(
    "Trades:",
    result["trades"]
)
