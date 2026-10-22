"""
مدیریت خروج از معامله؛ یک تابع مشترک برای بک‌تست و برای پیگیری سیگنال‌های زنده،
تا هر دو دقیقاً یک‌جور حساب شوند.

- حد ضرر و حد سود روی high/low هر کندل چک می‌شوند (نه فقط قیمت لحظه‌ی اسکن).
  اگر در یک کندل هر دو لمس شوند، بدبینانه «حد ضرر» حساب می‌شود.
- انتقال حد ضرر به نقطه‌ی سر‌به‌سر: وقتی قیمت breakeven_at_r برابرِ ریسک به سود
  رفت (پیش‌فرض ۱R)، از کندل بعد حد ضرر روی قیمتی می‌رود که با احتساب کارمزد
  ورود و خروج، نتیجه صفر شود. اگر بعد از آن حد ضرر بخورد، نتیجه BREAKEVEN است.
"""


def breakeven_price(direction, entry, fee_rate):

    """قیمتی که خروج در آن، بعد از کارمزد ورود و خروج، دقیقاً سود صفر بدهد."""

    if direction == "LONG":
        return entry * (1 + fee_rate) / (1 - fee_rate)
    return entry * (1 - fee_rate) / (1 + fee_rate)


def simulate_exit(direction, entry, stop, target, highs, lows, closes,
                  start, end, fee_rate, breakeven_at_r=None):

    """
    کندل‌های start تا end-1 (بعد از ورود) را بررسی می‌کند.
    خروجی: dict با result (WIN/LOSS/BREAKEVEN/OPEN)، exit_price، exit_index،
    current_stop (حد ضرر فعلی، شاید جابه‌جا شده) و moved_to_breakeven.
    OPEN یعنی هنوز به هیچ‌کدام نرسیده (فراخوان تصمیم می‌گیرد TIMEOUT/EXPIRED شود یا نه).
    """

    long_ = direction == "LONG"
    current_stop = stop
    moved = False
    trigger = None

    if breakeven_at_r is not None:
        risk = abs(entry - stop)
        trigger = entry + breakeven_at_r * risk if long_ else entry - breakeven_at_r * risk

    for j in range(start, end):

        hit_stop = lows[j] <= current_stop if long_ else highs[j] >= current_stop
        hit_target = highs[j] >= target if long_ else lows[j] <= target

        if hit_stop:
            return {"result": "BREAKEVEN" if moved else "LOSS", "exit_price": current_stop,
                    "exit_index": j, "current_stop": current_stop, "moved_to_breakeven": moved}

        if hit_target:
            return {"result": "WIN", "exit_price": target, "exit_index": j,
                    "current_stop": current_stop, "moved_to_breakeven": moved}

        if trigger is not None and not moved:
            reached = highs[j] >= trigger if long_ else lows[j] <= trigger
            if reached:
                moved = True
                current_stop = breakeven_price(direction, entry, fee_rate)

    last = end - 1 if end > start else start
    return {"result": "OPEN", "exit_price": closes[last] if end > start else None,
            "exit_index": last, "current_stop": current_stop, "moved_to_breakeven": moved}
