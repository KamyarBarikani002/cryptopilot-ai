from config.settings import ASSET_SYMBOLS
from src.risk_manager import calculate_stop_loss
from src.core.account import Account
from src.data.data_loader import MarketDataLoader
from src.data.candle_loader import CandleLoader
from src.analysis.analysis_loader import AnalysisLoader
from src.regime.regime_loader import RegimeLoader
from src.scoring.scoring_loader import ScoringLoader
from src.strategy.strategy_loader import StrategyLoader
from src.risk.risk_loader import RiskLoader
from src.report.report_loader import ReportLoader
from src.journal.journal_loader import JournalLoader


class CryptoPilotPipeline:

    def __init__(self):

        self.market = MarketDataLoader()
        self.candles = CandleLoader()
        self.analysis = AnalysisLoader()
        self.regime = RegimeLoader()
        self.scoring = ScoringLoader()
        self.strategy = StrategyLoader()
        self.risk = RiskLoader()
        self.report = ReportLoader()
        self.journal = JournalLoader()
        self.account = Account()

        print("Pipeline initialized")


    def run(self):

        prices = self.market.get_prices(ASSET_SYMBOLS)
        price = prices["BTC"]

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
            scoring["score"],
            analysis["rsi"]
        )

        # اندازه ریسک روی سرمایه واقعی الان حساب می‌شه، نه یک عدد ثابت
        capital_before, _ = self.account.portfolio_value(prices)

        risk = self.risk.analyze(
            capital_before,
            regime
        )

        stop_loss_price = calculate_stop_loss(
            price,
            risk["stop_loss_percent"]
        )

        contribution = self.account.apply_monthly_contribution(
            regime,
            prices
        )

        signal_action = self.account.apply_signal(
            decision,
            price,
            risk
        )

        self.account.save()

        portfolio_value, portfolio_breakdown = self.account.portfolio_value(prices)


        self.report.generate(
            price,
            analysis["ma"],
            analysis["rsi"],
            scoring["score"],
            decision
        )


        trade_data = {

            "asset": "BTC",
            "price": price,
            "decision": decision,
            "score": scoring["score"],
            "position_size": risk["position_size"],
            "stop_loss": stop_loss_price,
            "portfolio_value": portfolio_value,
            "cash": round(self.account.state["cash"], 2)

        }


        self.journal.save(
            trade_data
        )


        print("-----------------------")
        print("Risk Management")
        print("-----------------------")
        print("Capital Used For Sizing:", round(capital_before, 2), "$")
        print("Position Size:", risk["position_size"])
        print("Stop Loss:", round(stop_loss_price, 2))


        if contribution:

            print("-----------------------")
            print("Monthly Contribution")
            print("-----------------------")
            print("Period:", contribution["period"])
            print("Amount Added:", contribution["amount"], "$")
            print("Regime:", contribution["regime"])

            for asset, detail in contribution["allocation"].items():

                if asset == "Cash":
                    print(asset, ": $" + str(detail))
                else:
                    print(
                        asset,
                        ": $" + str(detail["usd"]),
                        "(", round(detail["units"], 6), "units @", detail["price"], ")"
                    )


        if signal_action:

            print("-----------------------")
            print("BTC Signal Action")
            print("-----------------------")
            print("Type:", signal_action["type"])
            print(
                "Amount: $" + str(signal_action["usd"]),
                "(", round(signal_action["units"], 6), "BTC @", signal_action["price"], ")"
            )


        print("-----------------------")
        print("Portfolio State")
        print("-----------------------")

        for asset, value in portfolio_breakdown.items():
            print(asset, ": $" + str(value))

        print("Total Portfolio Value:", portfolio_value, "$")
        print("Total Contributed:", round(self.account.state["total_contributed"], 2), "$")

        pnl = round(portfolio_value - self.account.state["total_contributed"], 2)
        print("Overall P&L:", pnl, "$")


        print("-----------------------")
        print("Trade Journal Saved")
        print("-----------------------")
