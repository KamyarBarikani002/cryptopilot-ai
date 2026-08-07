from src.risk.risk_loader import RiskLoader



loader = RiskLoader()


regimes = [

    "BULL",

    "NEUTRAL",

    "ACCUMULATION_ZONE",

    "BEAR"

]


capital = 10000



print("========================")
print("Risk Engine Report")
print("========================")


for regime in regimes:

    result = loader.analyze(
        capital,
        regime
    )


    print()

    print(
        "Regime:",
        regime
    )


    print(
        "Risk:",
        result["risk_percent"],
        "%"
    )


    print(
        "Risk Amount:",
        result["risk_amount"],
        "$"
    )


    print(
        "Stop Loss:",
        result["stop_loss_percent"],
        "%"
    )


    print(
        "Position Size:",
        result["position_size"],
        "$"
    )


    print(
        "Take Profit:",
        result["take_profit_percent"],
        "%"
    )


print()
print("========================")
