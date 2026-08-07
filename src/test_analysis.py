from technical_analysis import calculate_rsi, calculate_ma, generate_signal


prices = [
    63000,
    63200,
    63100,
    63500,
    63700,
    63800,
    63600,
    63900,
    64100,
    64000,
    64200,
    64300,
    64150,
    64400,
    64500,
    64300,
    64200,
    64600,
    64700,
    64800
]


ma = calculate_ma(prices)

rsi = calculate_rsi(prices)

signal = generate_signal(
    prices[-1],
    rsi,
    ma
)


print("MA:", ma)
print("RSI:", rsi)
print("SIGNAL:", signal)