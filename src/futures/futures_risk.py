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


def calculate_futures_trade_plan(
    direction,
    entry_price,
    capital,
    stop_loss_percent,
    risk_percent,
    reward_risk_ratio,
    max_leverage
):

    """
    برای یک فرصت Long یا Short، حد ضرر/حد سود/اهرم پیشنهادی/حجم پوزیشن رو
    بر مبنای ریسک ثابت (risk_percent از کل سرمایه) حساب می‌کند.

    این فقط یک پیشنهاد قاعده‌محور برای مدیریت ریسک است، نه تضمین سود یا
    تضمین جلوگیری از لیکویید شدن.
    """

    risk_amount = capital * (risk_percent / 100)

    position_size = risk_amount / (stop_loss_percent / 100)

    leverage = suggest_leverage(
        stop_loss_percent,
        max_leverage
    )

    # حجم پوزیشن رو به‌گونه‌ای محدود می‌کنیم که مارجین لازم از کل سرمایه بیشتر نشود
    max_position_size = capital * leverage
    position_size = min(position_size, max_position_size)

    margin_required = position_size / leverage

    if direction == "LONG":

        stop_loss_price = entry_price * (1 - stop_loss_percent / 100)

        take_profit_price = entry_price * (
            1 + (stop_loss_percent * reward_risk_ratio) / 100
        )

    else:  # SHORT

        stop_loss_price = entry_price * (1 + stop_loss_percent / 100)

        take_profit_price = entry_price * (
            1 - (stop_loss_percent * reward_risk_ratio) / 100
        )

    return {
        "entry_price": entry_price,
        "stop_loss_price": round(stop_loss_price, 6),
        "take_profit_price": round(take_profit_price, 6),
        "stop_loss_percent": round(stop_loss_percent, 2),
        "leverage": leverage,
        "position_size_usd": round(position_size, 2),
        "margin_required_usd": round(margin_required, 2),
        "risk_amount_usd": round(risk_amount, 2)
    }
