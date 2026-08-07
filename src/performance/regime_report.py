class RegimeReport:


    def analyze(
        self,
        regime_history
    ):

        report = {}


        for regime in regime_history:

            if regime not in report:
                report[regime] = 0

            report[regime] += 1



        total_days = len(
            regime_history
        )


        changes = 0


        previous = None


        for regime in regime_history:

            if previous is not None:

                if regime != previous:
                    changes += 1


            previous = regime



        dominant = None


        if report:

            dominant = max(
                report,
                key=report.get
            )



        percentages = {}


        for regime, days in report.items():

            percentages[regime] = round(
                (days / total_days) * 100,
                2
            )



        return {

            "days": report,

            "percentages": percentages,

            "changes": changes,

            "dominant": dominant

        }

