from monthly_investment import (
    add_monthly_capital,
    calculate_monthly_plan
)


capital = 200

monthly = 100

regime = "ACCUMULATION_ZONE"


new_capital = add_monthly_capital(
    capital,
    monthly
)


plan = calculate_monthly_plan(
    monthly,
    regime
)


print("================")
print("MONTHLY PLAN")
print("================")

print("Total Capital:", new_capital)


for coin, amount in plan.items():
    print(coin, ":", amount, "$")