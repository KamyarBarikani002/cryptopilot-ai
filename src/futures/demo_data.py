"""
داده‌ی نمایشی برای تست پنل بدون نیاز به اتصال اینترنت/کوکوین.
هیچ داده‌ی واقعی بازار نیست؛ فقط برای دیدن ظاهر و رفتار پنل استفاده می‌شود.
"""

_DEMO_SYMBOLS = [
    "XBTUSDTM",
    "ETHUSDTM",
    "SOLUSDTM",
    "DOGEUSDTM",
    "LINKUSDTM",
    "ONDOUSDTM",
    "NEARUSDTM",
    "XRPUSDTM",
    "PEPEUSDTM",
]

# این‌ها درصد تغییر هر کندل هستن (نه مقدار مطلق)؛ چون درصدی و ضربی اعمال
# می‌شن، قیمت هیچ‌وقت منفی یا غیرواقعی نمی‌شه، حتی وقتی الگو چند بار تکرار شود.
_WIGGLE = [0.8, 0.6, 0.7, -0.3, 0.75, 0.65, -0.25, 0.7, 0.6, -0.2]
_DEMO_START_MS = 1791417600000   # مضربی از ۴ ساعت، تا کندل‌های ۴ ساعته درست ساخته شوند


def synthetic_candles(direction, n=500, base_price=100.0, start_ms=_DEMO_START_MS):

    """
    کندل‌های ۱ ساعته‌ی ساختگی (با open/high/low/close/volume) برای دمو و تست:
    - "up": روند صعودی پرنوسان، بعد ۷ کندل اصلاح و در آخر یک کندل صعودی قوی
      با حجم بالا (دقیقاً الگوی «پولبک در جهت روند» که استراتژی دنبالش است)
    - "down": همین الگو برعکس
    - "flat": بازار رنج و بی‌جهت (نباید سیگنال بدهد)
    """

    sign = {"up": 1, "down": -1}.get(direction, 0)
    pullback = 7
    price = base_price
    candles = []

    for i in range(n):

        if sign == 0:
            change = 0.6 * ((i * 7919) % 11 - 5) / 5
        elif i < n - pullback - 1:
            change = sign * _WIGGLE[i % len(_WIGGLE)] * 0.5
        elif i < n - 1:
            change = -sign * 0.4
        else:
            change = sign * 1.0

        open_ = price
        close = price * (1 + change / 100)
        wick = abs(close - open_) * 0.3 + price * 0.001
        volume = 200.0 if (sign and i == n - 1) else 100.0

        candles.append([
            start_ms + i * 3_600_000, open_, max(open_, close) + wick,
            min(open_, close) - wick, close, volume,
        ])
        price = close

    return candles


def demo_top_symbols(top_n):

    return _DEMO_SYMBOLS[:top_n]


def demo_tick_size(symbol):

    return None


def demo_klines(symbol, interval, limit=500):

    """
    برای تنوع، هر نماد به‌صورت ثابت (بر اساس حروف اسمش) روی یکی از سه الگوی
    صعودی/نزولی/بی‌روند قرار می‌گیرد تا هم فرصت Long، هم Short، هم بازار بدون
    فرصت در دموی پنل دیده شود. PEPE با قیمت خیلی کوچک برای دیدن نمایش اعشار است.
    """

    direction = ("up", "down", "flat")[_demo_bucket(symbol)]
    candles = synthetic_candles(direction, max(limit, 300))[-limit:]

    # قیمت آخر را به یک قیمت واقعی‌نما برای همان ارز می‌رسانیم
    scale = _DEMO_LAST_PRICES.get(symbol, 1.0) / candles[-1][4]

    return [[c[0]] + [v * scale for v in c[1:5]] + [c[5]] for c in candles]


_DEMO_LAST_PRICES = {
    "XBTUSDTM": 82072.9, "ETHUSDTM": 2449.71, "SOLUSDTM": 106.374, "DOGEUSDTM": 0.08228,
    "LINKUSDTM": 12.6634, "ONDOUSDTM": 0.47388, "NEARUSDTM": 5.2823, "XRPUSDTM": 1.33852,
    "PEPEUSDTM": 0.0000040879,
}


def _demo_bucket(symbol):

    if symbol == "PEPEUSDTM":
        return 0   # در دمو حتماً یک فرصت با قیمت خیلی کوچک دیده شود

    seed = sum(ord(character) for character in symbol)
    return seed % 3


def demo_funding_rate(symbol):

    """
    داده نمایشی فاندینگ؛ برای الگوهای صعودی/نزولی قوی (bucket ۰ و ۱) به‌صورت
    «تاییدکننده» تنظیم شده (فاندینگ کمی خلاف جهت روند = فشرده‌شدن طرف مقابل =
    سیگنال ادامه‌ی روند) تا در دمو هم فرصت Long و هم Short واقعاً دیده شود؛
    برای الگوی بی‌روند (bucket ۲) خنثی است تا فیلتر فاندامنتال هم در دمو
    نمایش داده شود (یعنی هر امتیاز تکنیکالی به معنی سیگنال نهایی نیست).
    """

    bucket = _demo_bucket(symbol)

    if bucket == 0:    # الگوی صعودی -> شورت‌های کمی شلوغ (تاییدکننده ادامه صعود)
        return -0.01
    elif bucket == 1:  # الگوی نزولی -> لانگ‌های کمی شلوغ (تاییدکننده ادامه نزول)
        return 0.01
    else:
        return 0.0


def demo_open_interest_trend(symbol, period="1h", lookback=6):

    """
    داده نمایشی روند Open Interest؛ در الگوهای صعودی/نزولی قوی، OI رو به
    رشد در نظر می‌گیریم (روند تایید می‌شود)؛ در الگوی بی‌روند صفر است.
    """

    bucket = _demo_bucket(symbol)

    if bucket in (0, 1):
        return 10.0
    else:
        return 0.0


def demo_fear_greed_index():

    """
    مقدار خنثی (۵۰) تا رفتار حالت آزمایشی کاملاً از روی امتیاز تکنیکال/OI/
    فاندینگ همون نماد قابل پیش‌بینی باشد، بدون اینکه یک عدد سراسری روی همه
    نمادها اثر یک‌طرفه بگذارد.
    """

    return 50
