from src.data.data_loader import MarketDataLoader
from src.data.candle_loader import CandleLoader
from src.analysis.analysis_loader import AnalysisLoader
from src.regime.regime_loader import RegimeLoader
from src.scoring.scoring_loader import ScoringLoader
from src.strategy.strategy_loader import StrategyLoader
from src.risk.risk_loader import RiskLoader


class CryptoPilotPipeline:

    def __init__(self):

        self.market = MarketDataLoader()
        self.candles = CandleLoader()
        self.analysis = AnalysisLoader()
        self.regime = RegimeLoader()
        self.scoring = ScoringLoader()
        self.strategy = StrategyLoader()
        self.risk = RiskLoader()

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

        risk = self.risk.manage(
            200,
            2,
            price
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

        print("-----------------------")
        print("Risk Management")
        print("-----------------------")
        print("Position Size:", risk["position_size"])
        print("Stop Loss:", risk["stop_loss"])
