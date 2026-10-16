"""
اندیکاتورهای استاندارد روی کل سری کندل‌ها (هر خروجی هم‌طول ورودی است و جاهایی
که هنوز داده‌ی کافی نیست None دارد). هر مقدار در اندیس i فقط از کندل‌های 0..i
ساخته می‌شود، پس بک‌تست به آینده نگاه نمی‌کند.

RSI و ATR و ADX با روش Wilder (همان چیزی که TradingView و صرافی‌ها نشان می‌دهند).
"""


def ema(values, period):

    out = [None] * len(values)

    if len(values) < period:
        return out

    k = 2 / (period + 1)
    current = sum(values[:period]) / period
    out[period - 1] = current

    for i in range(period, len(values)):
        current = values[i] * k + current * (1 - k)
        out[i] = current

    return out


def _wilder_smooth(values, period, start):

    """میانگین Wilder از اندیس start به بعد (values[start-period+1 .. start] برای شروع)."""

    out = [None] * len(values)

    if len(values) <= start:
        return out

    current = sum(values[start - period + 1:start + 1]) / period
    out[start] = current

    for i in range(start + 1, len(values)):
        current = (current * (period - 1) + values[i]) / period
        out[i] = current

    return out


def rsi(closes, period=14):

    out = [None] * len(closes)

    if len(closes) <= period:
        return out

    gains = [0.0] + [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [0.0] + [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]

    avg_gain = _wilder_smooth(gains, period, period)
    avg_loss = _wilder_smooth(losses, period, period)

    for i in range(period, len(closes)):
        if avg_loss[i] == 0:
            out[i] = 100.0 if avg_gain[i] > 0 else 50.0
        else:
            out[i] = 100 - 100 / (1 + avg_gain[i] / avg_loss[i])

    return out


def true_range(highs, lows, closes):

    tr = [highs[0] - lows[0]]

    for i in range(1, len(closes)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    return tr


def atr(highs, lows, closes, period=14):

    if len(closes) <= period:
        return [None] * len(closes)

    return _wilder_smooth(true_range(highs, lows, closes), period, period)


def adx(highs, lows, closes, period=14):

    """قدرت روند (۰ تا ۱۰۰)؛ زیر ~۲۰ یعنی بازار بی‌روند و رنج."""

    n = len(closes)
    out = [None] * n

    if n <= 2 * period:
        return out

    plus_dm = [0.0]
    minus_dm = [0.0]

    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)

    tr_s = _wilder_smooth(true_range(highs, lows, closes), period, period)
    plus_s = _wilder_smooth(plus_dm, period, period)
    minus_s = _wilder_smooth(minus_dm, period, period)

    dx = [0.0] * n

    for i in range(period, n):
        if not tr_s[i]:
            continue
        plus_di = 100 * plus_s[i] / tr_s[i]
        minus_di = 100 * minus_s[i] / tr_s[i]
        total = plus_di + minus_di
        dx[i] = 0.0 if total == 0 else 100 * abs(plus_di - minus_di) / total

    smoothed = _wilder_smooth(dx, period, 2 * period - 1)

    for i in range(2 * period - 1, n):
        out[i] = smoothed[i]

    return out


def sma(values, period):

    out = [None] * len(values)
    running = 0.0

    for i, value in enumerate(values):
        running += value
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period

    return out
