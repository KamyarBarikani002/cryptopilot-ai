from src.strategy_engine import final_decision


class StrategyLoader:

    def decide(self, regime, score):

        return final_decision(
            regime,
            score
        )
