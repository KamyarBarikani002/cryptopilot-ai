from dca_manager import create_dca_plan


capital = 200

decision = "ACCUMULATE"


plan = create_dca_plan(
    capital,
    decision
)


print("================")
print("DCA PLAN")
print("================")


for step, amount in plan.items():
    print(step, ":", amount, "$")