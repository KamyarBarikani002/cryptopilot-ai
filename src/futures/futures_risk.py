def estimate_volatility_percent(closes, period=14):

    """
    میانگین درصد تغییرات مطلق قیمت در N کندل اخیر؛ یک تخمین ساده از نوسان
    (شبیه ATR درصدی) که برای تعیین فاصله حد ضرر متناسب با هر ارز استفاده می‌شود.
    """

    usable_period = min(period, len(closes) - 1)

    if usable_period < 2:
        return 2.0

    changes = []

    for i in range(1, usable_period + 1):

        previous_price = closes[-i - 1]
        current_price = closes[-i]

        if previous_price == 0:
            continue

        change_percent = abs(
            (current_price - previous_price) / previous_price
        ) * 100

        changes.append(change_percent)

    if not changes:
        return 2.0

    return sum(changes) / len(changes)


def suggest_stop_loss_percent(volatility_percent, min_stop=1.5, max_stop=15):

    return max(
        min_stop,
        min(volatility_percent * 2, max_stop)
    )


def suggest_leverage(stop_loss_percent, max_leverage, safety_factor=1.5):

    """
    اهرمی که فاصله‌ی تقریبی لیکویید شدن رو حداقل safety_factor برابر
    فاصله‌ی حد ضرر شما نگه می‌داره (تخمینی و محافظه‌کارانه، نه دقیق).

    توجه: قیمت لیکویید واقعی به مارجین نگهداری و کارمزد/فاندینگ صرافی هم
    بستگی دارد و ممکن است زودتر از این تخمین اتفاق بیفتد.
    """

    if stop_loss_percent <= 0:
        return 1

    raw_leverage = 100 / (safety_factor * stop_loss_percent)

    return max(1, min(round(raw_leverage, 1), max_leverage))


def _loss_per_unit(entry_price, stop_price, fee_rate):

    """زیان هر واحد اگر حد ضرر بخورد: فاصله تا حد ضرر + کارمزد ورود و خروج."""

    return abs(entry_price - stop_price) + fee_rate * (entry_price + stop_price)


def net_reward_risk(direction, entry_price, stop_price, take_profit_price, fee_rate):

    """نسبت سود خالص به زیان خالص (بعد از کارمزد ورود و خروج)."""

    loss = _loss_per_unit(entry_price, stop_price, fee_rate)

    if direction == "LONG":
        gain = (take_profit_price - entry_price) - fee_rate * (entry_price + take_profit_price)
    else:
        gain = (entry_price - take_profit_price) - fee_rate * (entry_price + take_profit_price)

    return gain / loss if loss > 0 else 0.0


def target_for_r(direction, entry_price, stop_price, reward_r, fee_rate, tick_size=None):

    """
    قیمتی که سود خالص (بعد از کارمزد ورود و خروج) در آن دقیقاً reward_r برابر
    زیان خالص حد ضرر باشد. رو به دورتر گرد می‌شود تا نسبت هیچ‌وقت کمتر نشود.
    """

    from src.price_format import round_to_tick

    needed_gain = reward_r * _loss_per_unit(entry_price, stop_price, fee_rate)

    if direction == "LONG":
        price = (needed_gain + entry_price * (1 + fee_rate)) / (1 - fee_rate)
        return round_to_tick(price, tick_size, "up")

    price = (entry_price * (1 - fee_rate) - needed_gain) / (1 + fee_rate)
    price = round_to_tick(price, tick_size, "down")
    if price <= 0:
        raise ValueError("take profit would be below zero")
    return price


def build_trade_plan(
    direction,
    entry_price,
    stop_price,
    capital,
    risk_percent,
    max_leverage,
    min_reward_risk=2.0,
    fee_percent=0.06,
    tick_size=None,
    scale_out=None,
):

    """
    پلن معامله با حد ضرر مشخص (از ساختار نمودار/ATR) و حد سودی که نسبت
    سود به ریسک را **بعد از کارمزد** دست‌کم min_reward_risk (پیش‌فرض ۱ به ۲)
    نگه می‌دارد.

    - حد ضرر و حد سود به گام قیمت (tickSize) همان قرارداد گرد می‌شوند؛ حد سود
      همیشه رو به دورتر گرد می‌شود تا نسبت هیچ‌وقت زیر حداقل نرود.
    - حجم پوزیشن طوری است که اگر حد ضرر بخورد (با کارمزد)، دقیقاً risk_percent
      از سرمایه از دست برود.

    این فقط یک پیشنهاد قاعده‌محور برای مدیریت ریسک است، نه تضمین سود یا
    تضمین جلوگیری از لیکویید شدن.
    """

    from src.price_format import round_to_tick

    if direction not in ("LONG", "SHORT"):
        raise ValueError("direction must be LONG or SHORT")

    fee_rate = fee_percent / 100

    stop_price = round_to_tick(stop_price, tick_size, "down" if direction == "LONG" else "up")

    if (direction == "LONG" and stop_price >= entry_price) or (direction == "SHORT" and stop_price <= entry_price):
        raise ValueError("stop must be on the losing side of the entry")

    loss = _loss_per_unit(entry_price, stop_price, fee_rate)
    take_profit = target_for_r(direction, entry_price, stop_price, min_reward_risk, fee_rate, tick_size)

    stop_loss_percent = abs(entry_price - stop_price) / entry_price * 100

    risk_amount = capital * (risk_percent / 100)
    quantity = risk_amount / loss
    position_size = quantity * entry_price

    leverage = suggest_leverage(stop_loss_percent, max_leverage)
    position_size = min(position_size, capital * leverage)

    plan = {
        "entry_price": entry_price,
        "stop_loss_price": stop_price,
        "take_profit_price": take_profit,
        "stop_loss_percent": round(stop_loss_percent, 2),
        "take_profit_percent": round(abs(take_profit - entry_price) / entry_price * 100, 2),
        "reward_risk_ratio": round(net_reward_risk(direction, entry_price, stop_price, take_profit, fee_rate), 2),
        "leverage": leverage,
        "position_size_usd": round(position_size, 2),
        "margin_required_usd": round(position_size / leverage, 2),
        "risk_amount_usd": round(risk_amount, 2),
        "fee_percent": fee_percent,
        "take_profit_1_price": None,
        "partial_fraction": None,
    }

    if scale_out:
        # خروج پله‌ای: بخشی از پوزیشن در tp1_r بسته می‌شود و حد ضرر بقیه به
        # نقطه‌ی سر‌به‌سر می‌رود؛ بقیه تا حد سود اصلی (min_reward_risk) می‌ماند.
        tp1 = target_for_r(direction, entry_price, stop_price, scale_out["tp1_r"], fee_rate, tick_size)
        fraction = scale_out["fraction"]
        plan["take_profit_1_price"] = tp1
        plan["partial_fraction"] = fraction
        plan["take_profit_1_percent"] = round(abs(tp1 - entry_price) / entry_price * 100, 2)
        plan["reward_risk_ratio"] = round(
            fraction * net_reward_risk(direction, entry_price, stop_price, tp1, fee_rate)
            + (1 - fraction) * net_reward_risk(direction, entry_price, stop_price, take_profit, fee_rate), 2)

    return plan
