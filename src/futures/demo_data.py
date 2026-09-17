"""
داده‌ی نمایشی برای تست پنل بدون نیاز به اتصال اینترنت/بایننس.
هیچ داده‌ی واقعی بازار نیست؛ فقط برای دیدن ظاهر و رفتار پنل استفاده می‌شود.
"""

_DEMO_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "DOGEUSDT",
    "LINKUSDT",
    "ONDOUSDT",
    "NEARUSDT",
    "XRPUSDT",
]

# این‌ها درصد تغییر هر کندل هستن (نه مقدار مطلق)؛ چون درصدی و ضربی اعمال
# می‌شن، قیمت هیچ‌وقت منفی یا غیرواقعی نمی‌شه، حتی وقتی الگو چند بار تکرار شود.
_UP_PATTERN = [0.8, 0.6, 0.7, -0.3, 0.75, 0.65, -0.25, 0.7, 0.6, -0.2]
_DOWN_PATTERN = [-0.8, -0.6, -0.7, 0.3, -0.75, -0.65, 0.25, -0.7, -0.6, 0.2]
_FLAT_PATTERN = [0.1, -0.1, 0.05, -0.05, 0.1, -0.1, 0.05, -0.05, 0.1, -0.1]


def _make_candles(closes):

    return [
        [0, 0, 0, 0, str(close), 0]
        for close in closes
    ]


def demo_top_symbols(top_n):

    return _DEMO_SYMBOLS[:top_n]


def demo_klines(symbol, interval, limit=100):

    """
    برای تنوع، هر نماد به‌صورت ثابت (بر اساس حروف اسمش) روی یکی از سه الگوی
    صعودی نویزی/نزولی نویزی/بی‌روند قرار می‌گیرد تا هم فرصت Long، هم Short،
    هم بازار بدون فرصت در دموی پنل دیده شود.
    """

    seed = sum(ord(character) for character in symbol)
    bucket = seed % 3

    if bucket == 0:
        pattern = _UP_PATTERN
        base_price = 100
    elif bucket == 1:
        pattern = _DOWN_PATTERN
        base_price = 200
    else:
        pattern = _FLAT_PATTERN
        base_price = 50

    price = base_price
    closes = []

    for i in range(30):
        percent_change = pattern[i % len(pattern)]
        price = price * (1 + percent_change / 100)
        closes.append(round(price, 6))

    return _make_candles(closes)


def _demo_bucket(symbol):

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
