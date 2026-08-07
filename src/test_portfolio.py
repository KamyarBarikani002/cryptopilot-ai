from portfolio_manager import create_portfolio


capital = 200

portfolio = create_portfolio(capital)


print("======================")
print("Portfolio Allocation")
print("======================")


for coin, amount in portfolio.items():
    print(
        coin,
        ":",
        amount,
        "$"
    )