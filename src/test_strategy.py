from strategy_engine import final_decision


regime = "ACCUMULATION_ZONE"
score = 50


decision = final_decision(
    regime,
    score
)


print("================")
print("Strategy Test")
print("================")

print(decision)