def create_dca_plan(capital, decision):

    if decision == "ACCUMULATE":

        plan = {
            "Entry 1": capital * 0.25,
            "Entry 2": capital * 0.25,
            "Entry 3": capital * 0.25,
            "Entry 4": capital * 0.25
        }

    elif decision == "BUY":

        plan = {
            "Immediate Buy": capital * 0.50,
            "Reserve": capital * 0.50
        }

    else:

        plan = {
            "WAIT": capital
        }

    return plan