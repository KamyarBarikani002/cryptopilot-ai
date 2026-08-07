from backtest_engine import simulate_dca


prices = [
    60000,
    58000,
    55000,
    62000,
    65000
]


result = simulate_dca(
    prices,
    100,
    200
)


print("================")
print("BACKTEST")
print("================")

print(
    "Final Value:",
    result
)