from src.technical_analysis import (
    calculate_ma,
    calculate_rsi,
    generate_signal
)


class AnalysisLoader:

    def analyze(self, candles, price):

        prices = [
            float(candle[4])
            for candle in candles
        ]

        ma = calculate_ma(prices)

        rsi = calculate_rsi(prices)

        signal = generate_signal(
            price,
            rsi,
            ma
        )

        return {
            "ma": ma,
            "rsi": rsi,
            "signal": signal
        }
