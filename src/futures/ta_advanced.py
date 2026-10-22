"""
ابزارهای پیشرفته‌تر تحلیل تکنیکال (همان جعبه‌ابزار کلاسیک کتاب‌های مرجع تحلیل
تکنیکال): MACD، باند بولینگر، استوکاستیک، OBV، کف و سقف‌های چرخشی (Swing)،
حمایت و مقاومت، واگرایی RSI، الگوهای کندلی و ساختار بازار.

قانون مهم برای بک‌تست: هیچ مقداری در اندیس i از کندل‌های بعد از i استفاده
نمی‌کند. کف/سقف چرخشی با «k کندل در هر طرف» فقط k کندل بعد قطعی می‌شود، پس از
همان لحظه به بعد در دسترس قرار می‌گیرد.
"""

import bisect

from src.futures import indicators as ind


# ---------------------------------------------------------------------------
# اندیکاتورها
# ---------------------------------------------------------------------------

def macd(closes, fast=12, slow=26, signal=9):

    fast_ema = ind.ema(closes, fast)
    slow_ema = ind.ema(closes, slow)
    line = [None if a is None or b is None else a - b for a, b in zip(fast_ema, slow_ema)]

    start = next((k for k, v in enumerate(line) if v is not None), None)
    signal_line = [None] * len(closes)
    if start is not None:
        tail = ind.ema(line[start:], signal)
        signal_line[start:] = tail

    hist = [None if a is None or b is None else a - b for a, b in zip(line, signal_line)]

    return {"macd": line, "macd_signal": signal_line, "macd_hist": hist}


def bollinger(closes, period=20, width=2.0):

    mid = ind.sma(closes, period)
    upper, lower, percent_b = [None] * len(closes), [None] * len(closes), [None] * len(closes)

    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        mean = mid[i]
        std = (sum((x - mean) ** 2 for x in window) / period) ** 0.5
        upper[i], lower[i] = mean + width * std, mean - width * std
        span = upper[i] - lower[i]
        percent_b[i] = (closes[i] - lower[i]) / span if span else 0.5

    return {"bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "bb_percent": percent_b}


def stochastic(highs, lows, closes, period=14, smooth=3):

    k = [None] * len(closes)

    for i in range(period - 1, len(closes)):
        hi = max(highs[i - period + 1:i + 1])
        lo = min(lows[i - period + 1:i + 1])
        k[i] = 50.0 if hi == lo else (closes[i] - lo) / (hi - lo) * 100

    d = [None] * len(closes)
    for i in range(len(closes)):
        window = k[max(0, i - smooth + 1):i + 1]
        if len(window) == smooth and all(v is not None for v in window):
            d[i] = sum(window) / smooth

    return {"stoch_k": k, "stoch_d": d}


def obv(closes, volumes):

    out = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            out.append(out[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            out.append(out[-1] - volumes[i])
        else:
            out.append(out[-1])
    return out


# ---------------------------------------------------------------------------
# کف و سقف چرخشی، حمایت و مقاومت
# ---------------------------------------------------------------------------

def swing_points(highs, lows, k=3):

    """
    سقف چرخشی: high[j] بیشترین مقدار در j-k..j+k. فقط در اندیس j+k قطعی می‌شود.
    خروجی: دو لیست از (j, قیمت, اندیس_قطعی_شدن).
    """

    swing_highs, swing_lows = [], []

    for j in range(k, len(highs) - k):
        window_h = highs[j - k:j + k + 1]
        window_l = lows[j - k:j + k + 1]
        if highs[j] == max(window_h) and window_h.count(highs[j]) == 1:
            swing_highs.append((j, highs[j], j + k))
        if lows[j] == min(window_l) and window_l.count(lows[j]) == 1:
            swing_lows.append((j, lows[j], j + k))

    return Swings(swing_highs), Swings(swing_lows)


class Swings(list):

    """لیست کف/سقف‌ها به‌همراه ایندکس‌های آماده برای جست‌وجوی دودویی."""

    def __init__(self, items):
        super().__init__(items)
        self.pivot_index = [x[0] for x in items]
        self.confirm_index = [x[2] for x in items]


def known_swings(swings, i, lookback=None):

    """
    کف/سقف‌هایی که تا کندل i قطعی شده‌اند (اختیاری: فقط در lookback کندل اخیر).
    swings بر اساس اندیس مرتب است و «اندیس قطعی شدن» = j + k هم صعودی است،
    پس با جست‌وجوی دودویی سریع پیدا می‌شوند (بک‌تست روی هزاران کندل).
    """

    if not swings:
        return []

    if not isinstance(swings, Swings):
        swings = Swings(swings)

    confirmed_upto = bisect.bisect_right(swings.confirm_index, i)
    start = 0
    if lookback is not None:
        start = bisect.bisect_left(swings.pivot_index, i - lookback, 0, confirmed_upto)

    return swings[start:confirmed_upto]


def nearest_levels(swing_highs, swing_lows, i, price, lookback=200):

    """نزدیک‌ترین حمایت زیر قیمت و مقاومت بالای قیمت، از کف/سقف‌های قطعی‌شده."""

    supports = [p for _, p, _ in known_swings(swing_lows, i, lookback) if p < price]
    resistances = [p for _, p, _ in known_swings(swing_highs, i, lookback) if p > price]

    return (max(supports) if supports else None, min(resistances) if resistances else None)


def market_structure(swing_highs, swing_lows, i):

    """
    +1: سقف‌ها و کف‌های بالاتر (روند صعودی)، -1: پایین‌تر (نزولی)، 0: نامشخص.
    دو سقف و دو کف آخرِ قطعی‌شده مقایسه می‌شوند.
    """

    highs = known_swings(swing_highs, i)[-2:]
    lows = known_swings(swing_lows, i)[-2:]

    if len(highs) < 2 or len(lows) < 2:
        return 0

    if highs[1][1] > highs[0][1] and lows[1][1] > lows[0][1]:
        return 1
    if highs[1][1] < highs[0][1] and lows[1][1] < lows[0][1]:
        return -1
    return 0


def rsi_divergence(swing_highs, swing_lows, rsi, i, max_age=12):

    """
    واگرایی معمولی بین دو کف/سقف آخر (قطعی‌شده، و آخری حداکثر max_age کندل پیش):
    +1 مثبت (قیمت کف پایین‌تر، RSI کف بالاتر) / -1 منفی / 0 هیچ.
    """

    lows = known_swings(swing_lows, i)[-2:]
    if len(lows) == 2 and i - lows[1][0] <= max_age:
        (j1, p1, _), (j2, p2, _) = lows
        if rsi[j1] is not None and rsi[j2] is not None and p2 < p1 and rsi[j2] > rsi[j1]:
            return 1

    highs = known_swings(swing_highs, i)[-2:]
    if len(highs) == 2 and i - highs[1][0] <= max_age:
        (j1, p1, _), (j2, p2, _) = highs
        if rsi[j1] is not None and rsi[j2] is not None and p2 > p1 and rsi[j2] < rsi[j1]:
            return -1

    return 0


# ---------------------------------------------------------------------------
# الگوهای کندلی (روی کندل بسته‌شده‌ی i)
# ---------------------------------------------------------------------------

def _body(o, c):
    return abs(c - o)


def candle_pattern(opens, highs, lows, closes, i):

    """
    (جهت، نام) یا (0, None). جهت +1 صعودی / -1 نزولی.
    الگوها: پوشای صعودی/نزولی، چکش/ستاره‌ی دنباله‌دار (پین‌بار)، ستاره‌ی صبحگاهی/شامگاهی.
    """

    if i < 2:
        return 0, None

    o, h, l, c = opens[i], highs[i], lows[i], closes[i]
    po, pc = opens[i - 1], closes[i - 1]
    rng = h - l

    if rng <= 0:
        return 0, None

    body = _body(o, c)
    upper = h - max(o, c)
    lower = min(o, c) - l

    # پوشا (Engulfing): بدنه‌ی فعلی بدنه‌ی قبلیِ خلاف‌جهت را کامل می‌پوشاند
    if c > o and pc < po and c >= po and o <= pc and body > _body(po, pc):
        return 1, "پوشای صعودی"
    if c < o and pc > po and c <= po and o >= pc and body > _body(po, pc):
        return -1, "پوشای نزولی"

    # پین‌بار: سایه‌ی بلند دست‌کم ۲ برابر بدنه و ۶۰٪ کل کندل، سایه‌ی مقابل کوتاه
    if lower >= 2 * body and lower >= 0.6 * rng and upper <= 0.2 * rng:
        return 1, "چکش / پین‌بار صعودی"
    if upper >= 2 * body and upper >= 0.6 * rng and lower <= 0.2 * rng:
        return -1, "ستاره‌ی دنباله‌دار / پین‌بار نزولی"

    # ستاره‌ی صبحگاهی/شامگاهی (۳ کندلی)
    o2, c2 = opens[i - 2], closes[i - 2]
    small_middle = _body(po, pc) <= 0.35 * _body(o2, c2)
    if c2 < o2 and small_middle and c > o and c > (o2 + c2) / 2:
        return 1, "ستاره‌ی صبحگاهی"
    if c2 > o2 and small_middle and c < o and c < (o2 + c2) / 2:
        return -1, "ستاره‌ی شامگاهی"

    return 0, None


# ---------------------------------------------------------------------------
# همه با هم
# ---------------------------------------------------------------------------

def add_advanced_indicators(data, swing_k=3):

    """اندیکاتورهای پیشرفته را به دیکشنری data (خروجی compute_indicators) اضافه می‌کند."""

    if "macd" in data:
        return data

    data.update(macd(data["close"]))
    data.update(bollinger(data["close"]))
    data.update(stochastic(data["high"], data["low"], data["close"]))
    data["obv"] = obv(data["close"], data["volume"])
    data["obv_ema"] = ind.ema(data["obv"], 20)
    data["swing_highs"], data["swing_lows"] = swing_points(data["high"], data["low"], swing_k)

    return data


def analysis_at(data, i):

    """
    خلاصه‌ی قابل‌خواندن تحلیل تکنیکال یک کندل (برای نمایش در پنل و توضیح سیگنال).
    """

    add_advanced_indicators(data)
    price = data["close"][i]
    support, resistance = nearest_levels(data["swing_highs"], data["swing_lows"], i, price)
    pattern_dir, pattern = candle_pattern(data["open"], data["high"], data["low"], data["close"], i)

    return {
        "price": price,
        "support": support,
        "resistance": resistance,
        "structure": market_structure(data["swing_highs"], data["swing_lows"], i),
        "divergence": rsi_divergence(data["swing_highs"], data["swing_lows"], data["rsi"], i),
        "pattern": pattern,
        "pattern_direction": pattern_dir,
        "macd_hist": data["macd_hist"][i],
        "stoch_k": data["stoch_k"][i],
        "bb_percent": data["bb_percent"][i],
        "obv_rising": data["obv_ema"][i] is not None and data["obv"][i] > data["obv_ema"][i],
    }
