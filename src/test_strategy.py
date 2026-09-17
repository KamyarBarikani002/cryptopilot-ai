from strategy_engine import final_decision


regime = "ACCUMULATION_ZONE"
score = 50
rsi = 40


decision = final_decision(
    regime,
    score,
    rsi
)


print("================")
print("Strategy Test")
print("================")

print(decision)