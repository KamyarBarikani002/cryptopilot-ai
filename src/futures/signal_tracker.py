import json
import os
from datetime import datetime, timedelta

from config.settings import SIGNAL_HISTORY_PATH, SIGNAL_MAX_OPEN_DAYS


def load_history():

    if not os.path.exists(SIGNAL_HISTORY_PATH):
        return []

    with open(SIGNAL_HISTORY_PATH, "r") as file:
        return json.load(file)


def save_history(history):

    directory = os.path.dirname(SIGNAL_HISTORY_PATH)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(SIGNAL_HISTORY_PATH, "w") as file:
        json.dump(history, file, indent=4)


def _find_open_record(history, symbol, direction):

    for record in history:

        if (
            record["symbol"] == symbol
            and record["direction"] == direction
            and record["status"] == "OPEN"
        ):
            return record

    return None


def record_new_signals(opportunities):

    """
    برای هر فرصت Long/Short تازه اسکن‌شده، اگر همین حالا یک سیگنال باز مشابه
    (همون ارز و همون جهت) از قبل ثبت نشده باشد، یک رکورد جدید با وضعیت OPEN
    ثبت می‌شود؛ این جلوی ثبت تکراری هر بار که دکمه اسکن زده می‌شود رو می‌گیرد.
    """

    history = load_history()
    added = 0

    for opportunity in opportunities:

        existing = _find_open_record(
            history,
            opportunity["symbol"],
            opportunity["direction"]
        )

        if existing is not None:
            continue

        history.append({
            "symbol": opportunity["symbol"],
            "direction": opportunity["direction"],
            "score": opportunity["score"],
            "entry_price": opportunity["entry_price"],
            "stop_loss_price": opportunity["stop_loss_price"],
            "take_profit_price": opportunity["take_profit_price"],
            "leverage": opportunity["leverage"],
            "status": "OPEN",
            "opened_at": str(datetime.now()),
            "closed_at": None,
            "closed_price": None
        })

        added += 1

    if added:
        save_history(history)

    return added


def _is_expired(record):

    opened_at = datetime.fromisoformat(record["opened_at"])

    return datetime.now() - opened_at > timedelta(days=SIGNAL_MAX_OPEN_DAYS)


def update_open_signals(price_fetcher):

    """
    price_fetcher باید یک تابع باشد که لیستی از نمادها می‌گیرد و دیکشنری
    {symbol: price} برمی‌گرداند (مثل get_futures_prices).

    هر سیگنال باز رو با قیمت فعلی چک می‌کند: اگر به حد سود یا حد ضرر رسیده
    باشد به‌عنوان WIN/LOSS بسته می‌شود؛ اگر خیلی وقته باز مانده، EXPIRED می‌شود.
    """

    history = load_history()

    open_records = [
        record
        for record in history
        if record["status"] == "OPEN"
    ]

    if not open_records:
        return 0

    symbols = list({record["symbol"] for record in open_records})

    try:
        prices = price_fetcher(symbols)
    except Exception:
        return 0

    updated = 0

    for record in open_records:

        current_price = prices.get(record["symbol"])

        outcome = None

        if current_price is not None:

            if record["direction"] == "LONG":

                if current_price >= record["take_profit_price"]:
                    outcome = "WIN"
                elif current_price <= record["stop_loss_price"]:
                    outcome = "LOSS"

            else:  # SHORT

                if current_price <= record["take_profit_price"]:
                    outcome = "WIN"
                elif current_price >= record["stop_loss_price"]:
                    outcome = "LOSS"

        if outcome is None and _is_expired(record):
            outcome = "EXPIRED"
            current_price = current_price if current_price is not None else record["entry_price"]

        if outcome is not None:
            record["status"] = outcome
            record["closed_at"] = str(datetime.now())
            record["closed_price"] = current_price
            updated += 1

    if updated:
        save_history(history)

    return updated


def calculate_pnl_percent(record):

    if record["closed_price"] is None:
        return None

    if record["direction"] == "LONG":

        change = (
            (record["closed_price"] - record["entry_price"])
            / record["entry_price"]
        ) * 100

    else:

        change = (
            (record["entry_price"] - record["closed_price"])
            / record["entry_price"]
        ) * 100

    return round(change, 2)


def get_stats(history=None):

    history = history if history is not None else load_history()

    closed = [
        record
        for record in history
        if record["status"] in ("WIN", "LOSS")
    ]

    wins = [
        record
        for record in closed
        if record["status"] == "WIN"
    ]

    win_rate = 0

    if closed:
        win_rate = round(len(wins) / len(closed) * 100, 2)

    return {
        "total": len(history),
        "open": len([r for r in history if r["status"] == "OPEN"]),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(closed) - len(wins),
        "expired": len([r for r in history if r["status"] == "EXPIRED"]),
        "win_rate": win_rate
    }
