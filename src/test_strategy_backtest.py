from src.backtest.backtest_loader import BacktestLoader


prices = [
    60000,
    59000,
    58000,
    57000,
    56000,
    55000,
    54000,
    53000,
    52000,
    51000,
    50000,
    51000,
    52000,
    54000,
    56000,
    58000,
    60000,
    63000,
    66000,
    70000,
    74000,
    78000,
    82000,
    85000,
    88000
]


engine = BacktestLoader()


report = engine.run(
    prices,
    200
)


print("========================")
print("CryptoPilot Backtest")
print("========================")

print(
    "Initial Capital :",
    report["initial_capital"],
    "$"
)

print(
    "Final Capital   :",
    report["final_capital"],
    "$"
)

print(
    "Profit          :",
    report["profit"],
    "$"
)

print(
    "Return          :",
    report["return_percent"],
    "%"
)

print(
    "Trades          :",
    report["trades"]
)


print()
print("========================")
print("Trade History")
print("========================")


for trade in report["trade_history"]:

    print()

    print(
        "Type:",
        trade["type"]
    )

    print(
        "Price:",
        trade["price"]
    )


    if "amount" in trade:

        print(
            "BTC Amount:",
            trade["amount"]
        )


    if "profit" in trade:

        print(
            "Profit:",
            trade["profit"],
            "$"
        )


print("========================")
