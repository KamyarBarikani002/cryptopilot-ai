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


# ---------------------------------------------------------------------------
# استراتژی «هم‌گرایی» (Confluence): چند تأیید مستقل تحلیل تکنیکال کلاسیک
# ---------------------------------------------------------------------------
#
# برای بالا بردن نرخ برد، فقط وقتی وارد می‌شویم که چند چیز با هم جور باشند:
# 1. روند: قیمت و EMA50 بالای EMA200 (Long) — معامله در جهت روند بزرگ‌تر.
# 2. محل: قیمت روی یک حمایت واقعی برگشته است (کف چرخشی اخیر، EMA50 یا باند
#    پایین بولینگر) — نه وسط هوا.
# 3. ماشه: یک الگوی کندلی برگشتی صعودی (پوشا، پین‌بار/چکش، ستاره‌ی صبحگاهی).
# 4. تأییدها (حداقل min_confirmations تا): واگرایی مثبت RSI، برگشت استوکاستیک از
#    اشباع فروش، رشد هیستوگرام MACD، حجم بالاتر از معمول، OBV بالای میانگینش.
# 5. جا برای حرکت: تا مقاومت بعدی دست‌کم به اندازه‌ی هدف (۲R) فاصله باشد.
# Short دقیقاً برعکس. حد ضرر زیر کف الگو/حمایت.

CONFLUENCE_DEFAULT_PARAMS = {
    "use_trend_filter": True,
    "min_confirmations": 2,
    "require_room": True,
    "room_r": 2.0,
    "level_lookback": 120,
    "near_level_atr": 0.5,
    "stop_buffer_atr": 0.2,
    "stop_atr_min": 0.5,
    "stop_atr_max": 3.0,
    "volume_ratio": 1.2,
    "use_funding_filter": True,
    "funding_crowded_percent": 0.05,
}

CONFLUENCE_MIN_CANDLES = 220


def confluence_signal_at(data, i, funding_percent=None, params=None):

    from src.futures import ta_advanced as ta

    p = {**CONFLUENCE_DEFAULT_PARAMS, **(params or {})}

    if i < CONFLUENCE_MIN_CANDLES - 1:
        return None

    ta.add_advanced_indicators(data)

    close, atr = data["close"][i], data["atr"][i]
    ema50, ema200 = data["ema50"][i], data["ema200"][i]

    if not atr or ema50 is None or ema200 is None or data["macd_hist"][i - 1] is None:
        return None

    pattern_dir, pattern = ta.candle_pattern(data["open"], data["high"], data["low"], data["close"], i)

    if pattern_dir == 0:
        return None

    up = pattern_dir == 1
    direction = "LONG" if up else "SHORT"

    if p["use_trend_filter"]:
        if up and not (close > ema200 and ema50 > ema200):
            return None
        if not up and not (close < ema200 and ema50 < ema200):
            return None

    support, resistance = ta.nearest_levels(
        data["swing_highs"], data["swing_lows"], i, close, p["level_lookback"]
    )
    near = p["near_level_atr"] * atr
    reasons = [pattern]

    # 2) محل: برگشت از یک سطح
    if up:
        touched = []
        if support is not None and data["low"][i] - near <= support <= close:
            touched.append(("حمایت کف قبلی", support))
        if data["low"][i] <= ema50 + 0.25 * atr and close > ema50:
            touched.append(("EMA50", ema50))
        if data["bb_lower"][i] is not None and data["low"][i] <= data["bb_lower"][i]:
            touched.append(("باند پایین بولینگر", data["bb_lower"][i]))
    else:
        touched = []
        if resistance is not None and close <= resistance <= data["high"][i] + near:
            touched.append(("مقاومت سقف قبلی", resistance))
        if data["high"][i] >= ema50 - 0.25 * atr and close < ema50:
            touched.append(("EMA50", ema50))
        if data["bb_upper"][i] is not None and data["high"][i] >= data["bb_upper"][i]:
            touched.append(("باند بالای بولینگر", data["bb_upper"][i]))

    if not touched:
        return None

    reasons += ["برگشت از " + name for name, _ in touched]

    # 4) تأییدها
    confirmations = []
    divergence = ta.rsi_divergence(data["swing_highs"], data["swing_lows"], data["rsi"], i)
    if divergence == pattern_dir:
        confirmations.append("واگرایی " + ("مثبت" if up else "منفی") + " RSI")

    k_now, d_now = data["stoch_k"][i], data["stoch_d"][i]
    recent_k = [v for v in data["stoch_k"][i - 3:i + 1] if v is not None]
    if k_now is not None and d_now is not None and recent_k:
        if up and min(recent_k) < 25 and k_now > d_now:
            confirmations.append("برگشت استوکاستیک از اشباع فروش")
        if not up and max(recent_k) > 75 and k_now < d_now:
            confirmations.append("برگشت استوکاستیک از اشباع خرید")

    hist_now, hist_prev = data["macd_hist"][i], data["macd_hist"][i - 1]
    if (up and hist_now > hist_prev) or (not up and hist_now < hist_prev):
        confirmations.append("هیستوگرام MACD در جهت معامله")

    if data["volume_sma"][i] and data["volume"][i] >= p["volume_ratio"] * data["volume_sma"][i]:
        confirmations.append("حجم بالاتر از معمول")

    if data["obv_ema"][i] is not None:
        if (up and data["obv"][i] > data["obv_ema"][i]) or (not up and data["obv"][i] < data["obv_ema"][i]):
            confirmations.append("OBV هم‌جهت")

    if len(confirmations) < p["min_confirmations"]:
        return None

    if p["use_funding_filter"] and funding_percent is not None:
        if up and funding_percent > p["funding_crowded_percent"]:
            return None
        if not up and funding_percent < -p["funding_crowded_percent"]:
            return None

    # حد ضرر: پشت کف/سقف الگو یا سطح، با کمی فاصله
    if up:
        anchor = min([data["low"][i], data["low"][i - 1]] + [lvl for _, lvl in touched if lvl < close])
        distance = close - (anchor - p["stop_buffer_atr"] * atr)
    else:
        anchor = max([data["high"][i], data["high"][i - 1]] + [lvl for _, lvl in touched if lvl > close])
        distance = (anchor + p["stop_buffer_atr"] * atr) - close

    if distance > p["stop_atr_max"] * atr:
        return None
    distance = max(distance, p["stop_atr_min"] * atr)
    stop = close - distance if up else close + distance

    if stop <= 0:
        return None

    # 5) جا برای حرکت تا مقاومت/حمایت بعدی
    if p["require_room"]:
        if up and resistance is not None and resistance - close < p["room_r"] * distance:
            return None
        if not up and support is not None and close - support < p["room_r"] * distance:
            return None

    structure = ta.market_structure(data["swing_highs"], data["swing_lows"], i)
    strength = 40 + 12 * len(confirmations) + (10 if structure == pattern_dir else 0)

    return {
        "direction": direction,
        "entry": close,
        "stop": stop,
        "strength": min(100, strength),
        "adx": round(data["adx"][i], 1) if data["adx"][i] is not None else None,
        "rsi": round(data["rsi"][i], 1) if data["rsi"][i] is not None else None,
        "atr_percent": round(atr / close * 100, 3),
        "trend_4h": data["trend_4h"][i],
        "reasons": reasons + confirmations,
        "support": support,
        "resistance": resistance,
    }


SIGNAL_FUNCTIONS = {
    "pullback": signal_at, "dip": dip_signal_at, "breakout": breakout_signal_at,
    "confluence": confluence_signal_at,
}
MIN_CANDLES_BY_STRATEGY = {
    "pullback": MIN_CANDLES, "dip": DIP_MIN_CANDLES, "breakout": BREAKOUT_MIN_CANDLES,
    "confluence": CONFLUENCE_MIN_CANDLES,
}

STRATEGY_TITLES = {
    "dip": "خرید افت در روند (MA20 + RSI)",
    "pullback": "پولبک در جهت روند (EMA + ADX)",
    "breakout": "شکست سقف/کف در جهت روند (Donchian)",
    "confluence": "هم‌گرایی تکنیکال (روند + سطح + الگوی کندلی + تأییدها)",
}


def latest_signal(candles, funding_percent=None, params=None, name="pullback"):

    """برای اسکنر زنده: سیگنال روی آخرین کندل بسته‌شده."""

    if len(candles) < MIN_CANDLES_BY_STRATEGY[name]:
        return None

    data = compute_indicators(candles)

    return SIGNAL_FUNCTIONS[name](data, len(candles) - 1, funding_percent, params)
