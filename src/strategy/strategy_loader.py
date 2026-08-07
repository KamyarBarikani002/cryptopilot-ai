from src.strategy_engine import final_decision


class StrategyLoader:

    def decide(
        self,
        regime,
        score,
        rsi
    ):

        return final_decision(
            regime,
            score,
            rsi
        )
