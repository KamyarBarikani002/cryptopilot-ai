from src.technical_analysis import calculate_ma, calculate_rsi


def extract_closes(candles):

    return [
        float(candle[4])
        for candle in candles
    ]


def calculate_direction_score(price, ma, rsi):

    """
    امتیاز جهت‌دار بازار، از -100 (فرصت شارت قوی) تا +100 (فرصت لانگ قوی).

    برخلاف calculate_score در technical_analysis که فقط برای فرصت‌های خرید (Long)
    طراحی شده، این نسخه به‌طور هم‌وزن هم به فرصت‌های Short حساس است.

    نکته طراحی مهم: معنای RSI رو نسبت به جهت روند (قیمت بالا/پایین میانگین متحرک)
    تفسیر می‌کنیم، نه به‌صورت مطلق. توی یک روند صعودی، RSI بالا یعنی مومنتوم
    صعودی قوی و تاییدشده (نه لزوماً سیگنال فروش)، و فقط یک افت ناگهانی RSI به
    زیر ۳۰ داخل همون روند صعودی به‌عنوان بهترین نقطه ورود لانگ (خرید در افت)
    در نظر گرفته می‌شود؛ به همین ترتیب برعکس برای روند نزولی.
    """

    uptrend = price > ma

    score = 40 if uptrend else -40

    if uptrend:

        if rsi < 30:
            score += 35   # افت شدید RSI داخل روند صعودی -> بهترین نقطه ورود Long
        elif rsi > 70:
            score += 20   # مومنتوم صعودی قوی و تاییدشده (ریسک اصلاح کوتاه‌مدت هم هست)
        elif rsi >= 50:
            score += 10   # مومنتوم صعودی سالم
        else:
            score -= 15   # مومنتوم در حال ضعیف شدن داخل روند صعودی -> احتیاط

    else:

        if rsi > 70:
            score -= 35   # صعود ناگهانی RSI داخل روند نزولی -> بهترین نقطه ورود Short
        elif rsi < 30:
            score -= 20   # مومنتوم نزولی قوی و تاییدشده
        elif rsi <= 50:
            score -= 10   # مومنتوم نزولی سالم
        else:
            score += 15   # مومنتوم در حال ضعیف شدن داخل روند نزولی -> احتیاط

    return max(-100, min(100, score))


def classify_opportunity(score, long_threshold, short_threshold):

    if score >= long_threshold:
        return "LONG"

    if score <= short_threshold:
        return "SHORT"

    return "NONE"


def analyze_symbol(symbol, candles):

    """
    فقط تحلیل تکنیکال خام رو برمی‌گرداند (بدون تصمیم نهایی Long/Short/None)؛
    تصمیم نهایی در scanner.py بعد از ترکیب با امتیاز فاندامنتال گرفته می‌شود
    (به همین دلیل اینجا آستانه‌ها دیگر لازم نیستند).
    """

    closes = extract_closes(candles)

    ma = calculate_ma(closes)
    rsi = calculate_rsi(closes)

    if ma is None or rsi is None:
        return None

    price = closes[-1]

    technical_score = calculate_direction_score(
        price,
        ma,
        rsi
    )

    return {
        "symbol": symbol,
        "price": price,
        "ma": round(ma, 6),
        "rsi": round(rsi, 2),
        "technical_score": technical_score
    }
