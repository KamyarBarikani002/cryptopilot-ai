from src.data.data_loader import MarketDataLoader
from src.data.candle_loader import CandleLoader
from src.analysis.analysis_loader import AnalysisLoader
from src.regime.regime_loader import RegimeLoader


class CryptoPilotPipeline:

    def __init__(self):

        self.market = MarketDataLoader()
        self.candles = CandleLoader()
        self.analysis = AnalysisLoader()
        self.regime = RegimeLoader()

        print("Pipeline initialized")


    def run(self):

        price = self.market.get_price()

        candles = self.candles.get_data()


        print("-----------------------")
        print("Market Data")
        print("-----------------------")
        print("BTC Price:", price)
        print("Candles:", len(candles))


        analysis = self.analysis.analyze(
            candles,
            price
        )


        print("-----------------------")
        print("Technical Analysis")
        print("-----------------------")
        print("MA20:", analysis["ma"])
        print("RSI:", analysis["rsi"])
        print("Signal:", analysis["signal"])


        regime = self.regime.detect(
            price,
            analysis["ma"],
            analysis["rsi"]
        )


        print("-----------------------")
        print("Market Regime")
        print("-----------------------")
        print(regime)
