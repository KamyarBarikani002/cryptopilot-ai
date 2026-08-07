from src.market_regime import detect_market_regime


class RegimeLoader:

    def detect(self, price, ma, rsi):

        return detect_market_regime(
            price,
            ma,
            rsi
        )
