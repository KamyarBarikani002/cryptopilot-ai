from datetime import datetime, timedelta

from config.settings import SIGNAL_MAX_OPEN_DAYS
from src.db.session import SessionLocal
from src.db.models import SignalRecord


def _row_to_dict(row):

    return {
        "id": row.id,
        "symbol": row.symbol,
        "direction": row.direction,
        "score": row.score,
        "entry_price": row.entry_price,
        "stop_loss_price": row.stop_loss_price,
        "take_profit_price": row.take_profit_price,
        "leverage": row.leverage,
        "status": row.status,
        "opened_at": row.opened_at,
        "closed_at": row.closed_at,
        "closed_price": row.closed_price
    }


def load_history():

    """
    تاریخچه سیگنال‌ها رو از دیتابیس می‌خونه (قبلاً از یک فایل JSON خونده
    می‌شد). خروجی همون شکل قبلی (لیستی از دیکشنری) رو داره، فقط الان هر
    دیکشنری یک "id" هم داره که برای ذخیره درست تغییرات در save_history لازمه.
    """

    session = SessionLocal()

    try:
        rows = session.query(SignalRecord).order_by(SignalRecord.id).all()
        return [_row_to_dict(row) for row in rows]
    finally:
        session.close()


def save_history(history):

    """
    لیست سیگنال‌ها رو با دیتابیس sync می‌کنه: رکوردهایی که "id" دارن
    (یعنی از load_history اومدن) آپدیت می‌شن، رکوردهای بدون "id" (سیگنال
    تازه از record_new_signals) به‌عنوان ردیف جدید insert می‌شن.
    """

    session = SessionLocal()

    try:

        existing_by_id = {
            row.id: row
            for row in session.query(SignalRecord).all()
        }

        for record in history:

            record_id = record.get("id")

            if record_id is not None and record_id in existing_by_id:

                row = existing_by_id[record_id]
                row.status = record["status"]
                row.closed_at = record["closed_at"]
                row.closed_price = record["closed_price"]

            else:

                session.add(SignalRecord(
                    symbol=record["symbol"],
                    direction=record["direction"],
                    score=record.get("score"),
                    entry_price=record["entry_price"],
                    stop_loss_price=record["stop_loss_price"],
                    take_profit_price=record["take_profit_price"],
                    leverage=record.get("leverage"),
                    status=record["status"],
                    opened_at=record["opened_at"],
                    closed_at=record.get("closed_at"),
                    closed_price=record.get("closed_price")
                ))

        session.commit()

    finally:
        session.close()


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
    new_records = []

    for opportunity in opportunities:

        existing = _find_open_record(
            history,
            opportunity["symbol"],
            opportunity["direction"]
        )

        if existing is not None:
            continue

        new_records.append({
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

    if new_records:
        save_history(new_records)

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

    updated_records = []

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
            updated_records.append(record)

    if updated_records:
        save_history(updated_records)

    return len(updated_records)


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
