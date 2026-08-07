import json
from datetime import datetime


def save_trade_log(data):

    data["time"] = str(datetime.now())

    try:
        with open(
            "trade_history.json",
            "r"
        ) as file:
            history = json.load(file)

    except:
        history = []


    history.append(data)


    with open(
        "trade_history.json",
        "w"
    ) as file:
        json.dump(
            history,
            file,
            indent=4
        )


def load_history():

    try:
        with open(
            "trade_history.json",
            "r"
        ) as file:
            return json.load(file)

    except:
        return []