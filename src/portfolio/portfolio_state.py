import json
import os

from config.settings import PORTFOLIO_STATE_PATH, INITIAL_CAPITAL


def _default_state():

    return {
        "cash": INITIAL_CAPITAL,
        "holdings": {},
        "total_contributed": INITIAL_CAPITAL,
        "last_contribution_period": None,
        "contributions": []
    }


def load_state():

    if not os.path.exists(PORTFOLIO_STATE_PATH):
        return _default_state()

    with open(PORTFOLIO_STATE_PATH, "r") as file:
        return json.load(file)


def save_state(state):

    directory = os.path.dirname(PORTFOLIO_STATE_PATH)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(PORTFOLIO_STATE_PATH, "w") as file:
        json.dump(state, file, indent=4)
