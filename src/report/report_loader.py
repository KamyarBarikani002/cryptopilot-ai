from src.report_generator import generate_report


class ReportLoader:

    def generate(
        self,
        price,
        ma,
        rsi,
        score,
        decision
    ):

        generate_report(
            price,
            ma,
            rsi,
            score,
            decision
        )
