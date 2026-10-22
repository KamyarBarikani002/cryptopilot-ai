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
        "closed_price": row.closed_price,
        "initial_stop_price": row.initial_stop_price,
        "take_profit_1_price": row.take_profit_1_price,
        "partial_fraction": row.partial_fraction,
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
                row.stop_loss_price = record["stop_loss_price"]   # ممکن است به سر‌به‌سر رفته باشد
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
                    closed_price=record.get("closed_price"),
                    initial_stop_price=record.get("initial_stop_price", record["stop_loss_price"]),
                    take_profit_1_price=record.get("take_profit_1_price"),
                    partial_fraction=record.get("partial_fraction"),
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
            "closed_price": None,
            "initial_stop_price": opportunity["stop_loss_price"],
            "take_profit_1_price": opportunity.get("take_profit_1_price"),
            "partial_fraction": opportunity.get("partial_fraction"),
        })

        added += 1

    if new_records:
        save_history(new_records)

    return added


def _is_expired(record):

    opened_at = datetime.fromisoformat(record["opened_at"])

    return datetime.now() - opened_at > timedelta(days=SIGNAL_MAX_OPEN_DAYS)


def _opened_ms(record):

    return int(datetime.fromisoformat(record["opened_at"]).timestamp() * 1000)


def update_open_signals(price_fetcher, candle_fetcher=None, breakeven_at_r=None, fee_percent=0.06):

    """
    سیگنال‌های باز را به‌روز می‌کند.

    - اگر candle_fetcher داده شود (symbol, from_ms) -> کندل‌های بسته‌شده‌ی ۱ ساعته
      از زمان ثبت سیگنال: حد سود/ضرر روی high/low همه‌ی کندل‌ها چک می‌شود (قبلاً
      فقط قیمت لحظه‌ی اسکن دیده می‌شد و برخورد بین دو اسکن از دست می‌رفت).
      انتقال به سر‌به‌سر هم دقیقاً مثل بک‌تست انجام می‌شود.
    - بعد قیمت لحظه‌ای (price_fetcher) هم با حد ضرر/سود فعلی مقایسه می‌شود.
    - سیگنالی که خیلی وقت باز مانده EXPIRED می‌شود.
    """

    from src.futures.exits import breakeven_price, simulate_exit, simulate_scaled_exit

    history = load_history()
    open_records = [record for record in history if record["status"] == "OPEN"]

    if not open_records:
        return 0

    try:
        prices = price_fetcher(list({record["symbol"] for record in open_records}))
    except Exception:
        prices = {}

    fee_rate = fee_percent / 100
    updated_records = []

    for record in open_records:

        outcome, closed_price = None, None
        long_ = record["direction"] == "LONG"
        stop_before = record["stop_loss_price"]
        initial_stop = record.get("initial_stop_price")
        already_moved = abs(stop_before - breakeven_price(
            record["direction"], record["entry_price"], fee_rate)) <= 1e-9 * record["entry_price"]
        # با حد ضرر اولیه، کل مسیر از ابتدا دوباره دقیقاً مثل بک‌تست شبیه‌سازی می‌شود.
        # سیگنال‌های قدیمی که حد ضرر اولیه ندارند، از حد ضرر فعلی ادامه می‌دهند.
        replay_stop = initial_stop if initial_stop else stop_before
        replay_from_start = bool(initial_stop)

        if candle_fetcher is not None:
            try:
                opened_ms = _opened_ms(record)
                candles = [c for c in candle_fetcher(record["symbol"], opened_ms) if c[0] >= opened_ms]
            except Exception:
                candles = []

            if candles and record.get("take_profit_1_price"):
                # خروج پله‌ای: همیشه از حد ضرر اولیه دوباره شبیه‌سازی می‌شود
                exit_info = simulate_scaled_exit(
                    record["direction"], record["entry_price"], replay_stop,
                    record["take_profit_1_price"], record["take_profit_price"],
                    [c[2] for c in candles], [c[3] for c in candles], [c[4] for c in candles],
                    0, len(candles), fee_rate,
                )
                if exit_info["result"] != "OPEN":
                    outcome, closed_price = exit_info["result"], exit_info["exit_price"]
                elif exit_info["tp1_index"] is not None:
                    record["stop_loss_price"] = exit_info["current_stop"]

            elif candles:
                exit_info = simulate_exit(
                    record["direction"], record["entry_price"], replay_stop,
                    record["take_profit_price"],
                    [c[2] for c in candles], [c[3] for c in candles], [c[4] for c in candles],
                    0, len(candles), fee_rate,
                    breakeven_at_r if (replay_from_start or not already_moved) else None,
                )
                if exit_info["result"] != "OPEN":
                    outcome, closed_price = exit_info["result"], exit_info["exit_price"]
                    if already_moved and not replay_from_start and outcome == "LOSS":
                        outcome = "BREAKEVEN"
                elif exit_info["moved_to_breakeven"]:
                    record["stop_loss_price"] = exit_info["current_stop"]

        current_price = prices.get(record["symbol"])

        if outcome is None and current_price is not None:

            moved = abs(record["stop_loss_price"] - breakeven_price(
                record["direction"], record["entry_price"], fee_rate)) <= 1e-9 * record["entry_price"]

            stopped_label = "LOSS"
            if moved:
                stopped_label = "PARTIAL" if record.get("take_profit_1_price") else "BREAKEVEN"

            if long_:
                if current_price >= record["take_profit_price"]:
                    outcome = "WIN"
                elif current_price <= record["stop_loss_price"]:
                    outcome = stopped_label
            else:
                if current_price <= record["take_profit_price"]:
                    outcome = "WIN"
                elif current_price >= record["stop_loss_price"]:
                    outcome = stopped_label

            closed_price = current_price

        if outcome is None and _is_expired(record):
            outcome = "EXPIRED"
            closed_price = current_price if current_price is not None else record["entry_price"]

        if outcome is not None:
            record["status"] = outcome
            record["closed_at"] = str(datetime.now())
            record["closed_price"] = closed_price
            updated_records.append(record)
        elif record["stop_loss_price"] != stop_before:
            updated_records.append(record)

    if updated_records:
        save_history(updated_records)

    return len(updated_records)


def _change_percent(record, price):

    sign = 1 if record["direction"] == "LONG" else -1
    return sign * (price - record["entry_price"]) / record["entry_price"] * 100


def calculate_pnl_percent(record):

    """
    درصد تغییر قیمت به نفع پوزیشن (بدون اهرم). در خروج پله‌ای، اگر پله‌ی اول
    گرفته شده باشد، میانگین وزنی پله‌ی اول و بقیه‌ی پوزیشن است.
    """

    if record["closed_price"] is None:
        return None

    change = _change_percent(record, record["closed_price"])

    if record.get("take_profit_1_price") and record["status"] in ("WIN", "PARTIAL"):
        fraction = record.get("partial_fraction") or 0.5
        change = fraction * _change_percent(record, record["take_profit_1_price"]) + (1 - fraction) * change

    return round(change, 2)


def get_stats(history=None):

    history = history if history is not None else load_history()

    closed = [
        record
        for record in history
        if record["status"] in ("WIN", "LOSS", "BREAKEVEN", "PARTIAL")
    ]

    wins = [
        record
        for record in closed
        if record["status"] == "WIN"
    ]

    win_rate = 0
    profit_rate = 0
    partials = [r for r in closed if r["status"] == "PARTIAL"]

    if closed:
        win_rate = round(len(wins) / len(closed) * 100, 2)
        profit_rate = round((len(wins) + len(partials)) / len(closed) * 100, 2)

    return {
        "total": len(history),
        "open": len([r for r in history if r["status"] == "OPEN"]),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len([r for r in closed if r["status"] == "LOSS"]),
        "breakevens": len([r for r in closed if r["status"] == "BREAKEVEN"]),
        "partials": len(partials),
        "expired": len([r for r in history if r["status"] == "EXPIRED"]),
        "win_rate": win_rate,
        # برد کامل + پله‌ی اول (معاملاتی که با سود بسته شدند)
        "profit_rate": profit_rate,
    }
