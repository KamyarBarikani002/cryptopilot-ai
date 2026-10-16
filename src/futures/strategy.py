"""
استراتژی سیگنال فیوچرز (نسخه‌ی ۲): «پولبک در جهت روند».

ایده: فقط در جهت روند غالب وارد شو، آن هم بعد از یک اصلاح کوتاه و وقتی قیمت
دوباره در جهت روند حرکت کرد؛ حد ضرر پشت آخرین کف/سقف ساختاری، حد سود با
نسبت حداقل ۱ به ۲ بعد از کارمزد.

شرط‌های Long (Short دقیقاً برعکس):
1. روند ۴ ساعته صعودی: قیمت بالای EMA50 چهارساعته و خود EMA50 رو به بالا.
2. روند ۱ ساعته صعودی: EMA50 بالای EMA200 و قیمت بالای EMA200.
3. روند واقعاً قوی باشد، نه بازار رنج: ADX ≥ ADX_MIN.
4. پولبک: در چند کندل اخیر قیمت تا حوالی EMA20 برگشته و RSI خنک شده، ولی
   ساختار نشکسته (کف‌ها بالای EMA50 منهای کمی ATR مانده).
5. ماشه: کندل فعلی صعودی بسته شده، بالای EMA20 و بالای سقف کندل قبل، RSI رو
   به بالا و هنوز اشباع خرید نیست، حجم معاملات کمتر از معمول نیست.
6. فیلتر فاندینگ: وقتی بازار بیش از حد شلوغ از لانگ است (فاندینگ خیلی مثبت)،
   لانگ پیشنهاد نمی‌شود.

همه‌ی محاسبه‌ها فقط از کندل‌های بسته‌شده‌ی تا همان لحظه استفاده می‌کنند؛ همین
تابع هم در اسکنر زنده و هم در بک‌تست استفاده می‌شود.
"""

from src.futures import indicators as ind

HOUR_MS = 3_600_000
FOUR_HOURS_MS = 4 * HOUR_MS

# پارامترها (در بک‌تست قابل تغییرند)
DEFAULT_PARAMS = {
    "adx_min": 20,
    "pullback_lookback": 6,
    "pullback_rsi": 45,          # RSI در پولبک لانگ باید دست‌کم یک بار زیر این برود
    "trigger_rsi_max": 70,       # اگر RSI از این بالاتر است، دیر شده
    "swing_lookback": 10,
    "stop_atr_buffer": 0.25,
    "stop_atr_min": 1.0,
    "stop_atr_max": 3.0,
    "volume_ratio_min": 0.8,
    "funding_crowded_percent": 0.05,   # فاندینگ ۸ ساعته به درصد
    "use_4h_filter": True,
    "use_adx_filter": True,
}

MIN_CANDLES = 260


def compute_indicators(candles):

    """candles: [[time_ms, open, high, low, close, volume], ...] از قدیم به جدید."""

    times = [int(c[0]) for c in candles]
    opens = [float(c[1]) for c in candles]
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]
    closes = [float(c[4]) for c in candles]
    volumes = [float(c[5]) for c in candles]

    data = {
        "time": times, "open": opens, "high": highs, "low": lows,
        "close": closes, "volume": volumes,
        "ema20": ind.ema(closes, 20),
        "ema50": ind.ema(closes, 50),
        "ema200": ind.ema(closes, 200),
        "rsi": ind.rsi(closes, 14),
        "atr": ind.atr(highs, lows, closes, 14),
        "adx": ind.adx(highs, lows, closes, 14),
        "volume_sma": ind.sma(volumes, 20),
    }

    data.update(_four_hour_trend(times, closes))

    return data


def _four_hour_trend(times, closes):

    """
    کندل‌های ۴ ساعته از روی ۱ ساعته ساخته می‌شوند. برای هر کندل ۱ ساعته فقط
    کندل‌های ۴ ساعته‌ای که تا آن لحظه کامل بسته شده‌اند حساب می‌شوند.
    """

    closes_4h = []
    completed_count = []   # برای هر اندیس ۱ ساعته: چند کندل ۴ ساعته‌ی کامل داریم

    for i, t in enumerate(times):
        if (t + HOUR_MS) % FOUR_HOURS_MS == 0:
            closes_4h.append(closes[i])
        completed_count.append(len(closes_4h))

    ema50_4h = ind.ema(closes_4h, 50)

    trend = []
    for count in completed_count:
        j = count - 1
        if j < 3 or ema50_4h[j] is None or ema50_4h[j - 3] is None:
            trend.append(0)
            continue
        if closes_4h[j] > ema50_4h[j] and ema50_4h[j] > ema50_4h[j - 3]:
            trend.append(1)
        elif closes_4h[j] < ema50_4h[j] and ema50_4h[j] < ema50_4h[j - 3]:
            trend.append(-1)
        else:
            trend.append(0)

    return {"trend_4h": trend}


def _ready(data, i, params):

    keys = ("ema20", "ema50", "ema200", "rsi", "atr", "volume_sma")
    if params["use_adx_filter"]:
        keys += ("adx",)
    lookback = max(params["pullback_lookback"], params["swing_lookback"])
    return i >= lookback and all(data[k][i] is not None for k in keys) and data["rsi"][i - 1] is not None


def signal_at(data, i, funding_percent=None, params=None):

    """
    سیگنال روی کندل بسته‌شده‌ی i، یا None. خروجی:
    {direction, entry, stop, strength (0..100), reasons}
    """

    params = {**DEFAULT_PARAMS, **(params or {})}

    if not _ready(data, i, params):
        return None

    close, open_ = data["close"][i], data["open"][i]
    ema20, ema50, ema200 = data["ema20"][i], data["ema50"][i], data["ema200"][i]
    rsi_now, rsi_prev = data["rsi"][i], data["rsi"][i - 1]
    atr = data["atr"][i]
    adx = data["adx"][i] if data["adx"][i] is not None else 0.0
    trend_4h = data["trend_4h"][i]

    if atr <= 0:
        return None

    if params["use_adx_filter"] and adx < params["adx_min"]:
        return None

    if data["volume_sma"][i] and data["volume"][i] < params["volume_ratio_min"] * data["volume_sma"][i]:
        return None

    window = range(i - params["pullback_lookback"], i)
    swing = range(i - params["swing_lookback"] + 1, i + 1)
    crowded = params["funding_crowded_percent"]

    for direction in ("LONG", "SHORT"):

        up = direction == "LONG"
        sign = 1 if up else -1

        if params["use_4h_filter"] and trend_4h != sign:
            continue

        if up and not (ema50 > ema200 and close > ema200):
            continue
        if not up and not (ema50 < ema200 and close < ema200):
            continue

        if up:
            touched = any(data["low"][k] <= data["ema20"][k] * 1.001 for k in window)
            cooled = min(data["rsi"][k] for k in window) <= params["pullback_rsi"]
            intact = min(data["low"][k] - data["ema50"][k] for k in window) >= -0.5 * atr
            trigger = (
                close > open_ and close > ema20 and close > data["high"][i - 1]
                and rsi_now > rsi_prev and rsi_now <= params["trigger_rsi_max"]
            )
        else:
            touched = any(data["high"][k] >= data["ema20"][k] * 0.999 for k in window)
            cooled = max(data["rsi"][k] for k in window) >= 100 - params["pullback_rsi"]
            intact = max(data["high"][k] - data["ema50"][k] for k in window) <= 0.5 * atr
            trigger = (
                close < open_ and close < ema20 and close < data["low"][i - 1]
                and rsi_now < rsi_prev and rsi_now >= 100 - params["trigger_rsi_max"]
            )

        if not (touched and cooled and intact and trigger):
            continue

        if funding_percent is not None:
            if up and funding_percent > crowded:
                continue
            if not up and funding_percent < -crowded:
                continue

        if up:
            structural = min(data["low"][k] for k in swing) - params["stop_atr_buffer"] * atr
            distance = close - structural
        else:
            structural = max(data["high"][k] for k in swing) + params["stop_atr_buffer"] * atr
            distance = structural - close

        if distance > params["stop_atr_max"] * atr:
            continue   # ساختار خیلی دور است؛ ریسک بیش از حد بزرگ می‌شود
        distance = max(distance, params["stop_atr_min"] * atr)

        stop = close - distance if up else close + distance

        if stop <= 0:
            continue

        strength = _strength(adx, rsi_now, up, data["volume"][i], data["volume_sma"][i], close, ema20, atr)

        return {
            "direction": direction,
            "entry": close,
            "stop": stop,
            "strength": strength,
            "adx": round(adx, 1),
            "rsi": round(rsi_now, 1),
            "atr_percent": round(atr / close * 100, 3),
            "trend_4h": trend_4h,
        }

    return None


def _strength(adx, rsi_now, up, volume, volume_sma, close, ema20, atr):

    """
    امتیاز ۰ تا ۱۰۰ برای مرتب کردن سیگنال‌ها (نه شرط ورود):
    قدرت روند (ADX)، جای خالی RSI تا اشباع، حجم، و نزدیکی ورود به EMA20.
    """

    trend = min(max((adx - 20) / 20, 0), 1) * 35
    room = (70 - rsi_now) / 25 if up else (rsi_now - 30) / 25
    room = min(max(room, 0), 1) * 25
    vol = min(max((volume / volume_sma - 0.8) / 1.2, 0), 1) * 20 if volume_sma else 10
    stretch = abs(close - ema20) / atr if atr else 1
    tight = min(max(1 - stretch / 1.5, 0), 1) * 20

    return round(trend + room + vol + tight)


# ---------------------------------------------------------------------------
# استراتژی «خرید افت در روند» (منطق قبلی اسکنر، با حد سود/ضرر جدید)
# ---------------------------------------------------------------------------
#
# Long: قیمت بالای میانگین ۲۰ کندل (روند صعودی کوتاه‌مدت) ولی RSI زیر ۳۰، یعنی
# یک افت تند داخل روند صعودی. Short برعکس: زیر میانگین و RSI بالای ۷۰.
# در بک‌تست ۱۸۰ روزه روی ۳۰ ارز کوکوین از «پولبک در جهت روند» بهتر بود، برای
# همین الان استراتژی پیش‌فرض اسکنر است. فیلترهای اضافه پیش‌فرض خاموش‌اند و در
# صفحه‌ی بک‌تست با هم مقایسه می‌شوند.

DIP_DEFAULT_PARAMS = {
    "rsi_low": 30,
    "rsi_high": 70,
    "use_ema200_filter": False,
    "adx_min": None,
    "use_funding_filter": False,
    "funding_crowded_percent": 0.05,
}

DIP_MIN_CANDLES = 100


def dip_signal_at(data, i, funding_percent=None, params=None):

    from src.futures.futures_risk import estimate_volatility_percent, suggest_stop_loss_percent
    from src.technical_analysis import calculate_ma, calculate_rsi

    p = {**DIP_DEFAULT_PARAMS, **(params or {})}

    if i < DIP_MIN_CANDLES - 1:
        return None

    closes = data["close"][i - DIP_MIN_CANDLES + 1:i + 1]
    ma = calculate_ma(closes)
    rsi_now = calculate_rsi(closes)

    if ma is None or rsi_now is None:
        return None

    price = closes[-1]

    if price > ma and rsi_now < p["rsi_low"]:
        direction = "LONG"
    elif price < ma and rsi_now > p["rsi_high"]:
        direction = "SHORT"
    else:
        return None

    up = direction == "LONG"

    if p["use_ema200_filter"]:
        ema200 = data["ema200"][i]
        if ema200 is None or (up and price <= ema200) or (not up and price >= ema200):
            return None

    adx = data["adx"][i]
    if p["adx_min"] is not None and (adx is None or adx < p["adx_min"]):
        return None

    if p["use_funding_filter"] and funding_percent is not None:
        if up and funding_percent > p["funding_crowded_percent"]:
            return None
        if not up and funding_percent < -p["funding_crowded_percent"]:
            return None

    stop_percent = suggest_stop_loss_percent(estimate_volatility_percent(closes))
    stop = price * (1 - stop_percent / 100) if up else price * (1 + stop_percent / 100)

    # هرچه RSI از ۳۰ (یا ۷۰) دورتر، افت/جهش تندتر -> امتیاز بیشتر (فقط برای ترتیب)
    depth = (p["rsi_low"] - rsi_now) if up else (rsi_now - p["rsi_high"])
    strength = round(50 + min(max(depth, 0), 25) * 2)

    atr = data["atr"][i]

    return {
        "direction": direction,
        "entry": price,
        "stop": stop,
        "strength": strength,
        "adx": round(adx, 1) if adx is not None else None,
        "rsi": round(rsi_now, 1),
        "atr_percent": round(atr / price * 100, 3) if atr else None,
        "trend_4h": data["trend_4h"][i],
    }


# ---------------------------------------------------------------------------
# استراتژی «شکست سقف/کف» (Donchian breakout، روندگیر کلاسیک)
# ---------------------------------------------------------------------------
#
# Long: کندل بالای بالاترین سقف N کندل قبل بسته شود، قیمت بالای EMA200 باشد
# (روند بلندمدت صعودی)، روند قوی باشد (ADX) و حجم کندل کمتر از معمول نباشد.
# Short برعکس. حد ضرر چند برابر ATR زیر ورود.

BREAKOUT_DEFAULT_PARAMS = {
    "lookback": 48,
    "use_ema200_filter": True,
    "adx_min": 20,
    "stop_atr": 2.0,
    "volume_ratio_min": 1.0,
    "use_funding_filter": True,
    "funding_crowded_percent": 0.05,
}

BREAKOUT_MIN_CANDLES = 220


def breakout_signal_at(data, i, funding_percent=None, params=None):

    p = {**BREAKOUT_DEFAULT_PARAMS, **(params or {})}
    n = p["lookback"]

    if i < max(n + 1, BREAKOUT_MIN_CANDLES - 1):
        return None

    close = data["close"][i]
    atr = data["atr"][i]
    ema200 = data["ema200"][i]
    adx = data["adx"][i]
    volume_sma = data["volume_sma"][i]

    if not atr or ema200 is None or adx is None:
        return None

    highest = max(data["high"][i - n:i])
    lowest = min(data["low"][i - n:i])
    # فقط اولین کندلی که شکست را می‌سازد (کندل قبلی هنوز داخل کانال بسته شده بود)
    previous_highest = max(data["high"][i - n - 1:i - 1])
    previous_lowest = min(data["low"][i - n - 1:i - 1])

    if close > highest and data["close"][i - 1] <= previous_highest:
        direction = "LONG"
    elif close < lowest and data["close"][i - 1] >= previous_lowest:
        direction = "SHORT"
    else:
        return None

    up = direction == "LONG"

    if p["use_ema200_filter"] and ((up and close <= ema200) or (not up and close >= ema200)):
        return None

    if p["adx_min"] is not None and adx < p["adx_min"]:
        return None

    if volume_sma and data["volume"][i] < p["volume_ratio_min"] * volume_sma:
        return None

    if p["use_funding_filter"] and funding_percent is not None:
        if up and funding_percent > p["funding_crowded_percent"]:
            return None
        if not up and funding_percent < -p["funding_crowded_percent"]:
            return None

    stop = close - p["stop_atr"] * atr if up else close + p["stop_atr"] * atr

    if stop <= 0:
        return None

    volume_boost = min(max((data["volume"][i] / volume_sma - 1) / 2, 0), 1) * 40 if volume_sma else 20
    strength = round(40 + min(max((adx - 20) / 20, 0), 1) * 20 + volume_boost)

    return {
        "direction": direction,
        "entry": close,
        "stop": stop,
        "strength": strength,
        "adx": round(adx, 1),
        "rsi": round(data["rsi"][i], 1) if data["rsi"][i] is not None else None,
        "atr_percent": round(atr / close * 100, 3),
        "trend_4h": data["trend_4h"][i],
    }


SIGNAL_FUNCTIONS = {"pullback": signal_at, "dip": dip_signal_at, "breakout": breakout_signal_at}
MIN_CANDLES_BY_STRATEGY = {
    "pullback": MIN_CANDLES, "dip": DIP_MIN_CANDLES, "breakout": BREAKOUT_MIN_CANDLES,
}

STRATEGY_TITLES = {
    "dip": "خرید افت در روند (MA20 + RSI)",
    "pullback": "پولبک در جهت روند (EMA + ADX)",
    "breakout": "شکست سقف/کف در جهت روند (Donchian)",
}


def latest_signal(candles, funding_percent=None, params=None, name="pullback"):

    """برای اسکنر زنده: سیگنال روی آخرین کندل بسته‌شده."""

    if len(candles) < MIN_CANDLES_BY_STRATEGY[name]:
        return None

    data = compute_indicators(candles)

    return SIGNAL_FUNCTIONS[name](data, len(candles) - 1, funding_percent, params)
