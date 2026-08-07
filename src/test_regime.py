from market_regime import detect_market_regime


price = 63500
ma = 64300
rsi = 17


regime = detect_market_regime(
    price,
    ma,
    rsi
)


print("================")
print("Market Regime")
print("================")

print(regime)