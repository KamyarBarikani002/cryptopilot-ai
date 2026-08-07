from src.data.data_loader import MarketDataLoader
from src.data.candle_loader import CandleLoader
from src.analysis.analysis_loader import AnalysisLoader
from src.regime.regime_loader import RegimeLoader
from src.scoring.scoring_loader import ScoringLoader
from src.strategy.strategy_loader import StrategyLoader


class CryptoPilotPipeline:

    def __init__(self):

        self.market = MarketDataLoader()
        self.candles = CandleLoader()
        self.analysis = AnalysisLoader()
        self.regime = RegimeLoader()
        self.scoring = ScoringLoader()
        self.strategy = StrategyLoader()

        print("Pipeline initialized")


    def run(self):

        price = self.market.get_price()

        candles = self.candles.get_data()


        analysis = self.analysis.analyze(
            candles,
            price
        )


        regime = self.regime.detect(
            price,
            analysis["ma"],
            analysis["rsi"]
        )


        scoring = self.scoring.calculate(
            price,
            analysis["ma"],
            analysis["rsi"]
        )


        decision = self.strategy.decide(
            regime,
            scoring["score"]
        )


        print("-----------------------")
        print("CryptoPilot AI Decision")
        print("-----------------------")
        print("BTC Price:", price)
        print("MA20:", analysis["ma"])
        print("RSI:", analysis["rsi"])
        print("Regime:", regime)
        print("Score:", scoring["score"])
        print("Decision:", decision)
