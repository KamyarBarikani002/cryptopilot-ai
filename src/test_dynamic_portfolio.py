from dynamic_portfolio import create_dynamic_portfolio


capital = 200

regime = "ACCUMULATION_ZONE"


portfolio = create_dynamic_portfolio(
    capital,
    regime
)


print("======================")
print("Dynamic Portfolio")
print("======================")


for coin, amount in portfolio.items():
    print(coin, ":", amount, "$")