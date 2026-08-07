from src.scoring_engine import calculate_score, get_decision


class ScoringLoader:

    def calculate(self, price, ma, rsi):

        score = calculate_score(
            price,
            ma,
            rsi
        )

        decision = get_decision(score)

        return {
            "score": score,
            "decision": decision
        }
