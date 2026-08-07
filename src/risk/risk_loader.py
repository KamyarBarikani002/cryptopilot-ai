from src.risk.risk_engine import calculate_risk


class RiskLoader:


    def analyze(
        self,
        capital,
        regime
    ):

        return calculate_risk(
            capital,
            regime
        )
