from candle_data import get_btc_candles
from technical_analysis import calculate_rsi, calculate_ma
from scoring_engine import calculate_score
from market_regime import detect_market_regime
from dynamic_portfolio import create_dynamic_portfolio
from strategy_engine import final_decision


capital = 200


# دریافت داده بازار

candles = get_btc_candles()


prices = []

for candle in candles:
    prices.append(float(candle[4]))


price = prices[-1]


# تحلیل تکنیکال

ma = calculate_ma(prices)

rsi = calculate_rsi(prices)


# امتیاز بازار

score = calculate_score(
    price,
    ma,
    rsi
)


# تشخیص وضعیت بازار

regime = detect_market_regime(
    price,
    ma,
    rsi
)


# ساخت پرتفوی

portfolio = create_dynamic_portfolio(
    capital,
    regime
)


# تصمیم نهایی

decision = final_decision(
    regime,
    score,
    rsi
)


# گزارش

print("==============================")
print("      CryptoPilot AI v1.0")
print("==============================")

print()

print("BTC Price:", round(price,2))
print("MA20:", round(ma,2))
print("RSI:", round(rsi,2))

print("------------------------------")

print("Market Regime:", regime)
print("Score:", score)

print("------------------------------")

print("Portfolio Plan:")

for coin, amount in portfolio.items():
    print(
        coin,
        ":",
        round(amount,2),
        "$"
    )

print("------------------------------")

print("FINAL DECISION:")
print(decision)

print("==============================")