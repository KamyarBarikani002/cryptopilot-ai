import requests

from config.settings import FUTURES_BASE_URL, FEAR_GREED_API_URL


def get_funding_rate(symbol):

    """
    نرخ فاندینگ فعلی (٪) قرارداد پرپچوال. فاندینگ مثبت یعنی لانگ‌ها به شورت‌ها
    پول می‌دهند (بازار شلوغ از لانگ -> ریسک اصلاح/برگشت به سمت شورت)، فاندینگ
    منفی برعکس (بازار شلوغ از شورت -> ریسک برگشت به سمت لانگ). این یک سیگنال
    "خلاف جهت جمعیت" (contrarian) است، نه تاییدی.
    """

    url = FUTURES_BASE_URL + "/fapi/v1/premiumIndex"

    params = {"symbol": symbol}

    response = requests.get(url, params=params)

    data = response.json()

    return float(data["lastFundingRate"]) * 100


def get_open_interest_trend(symbol, period="1h", lookback=6):

    """
    درصد تغییر Open Interest (مجموع پوزیشن‌های باز) طی چند کندل اخیر.
    این یک سیگنال "تاییدی" است: اگر همراه با روند قیمت باشد (مثلاً قیمت و OI
    هر دو در حال رشد)، یعنی پول تازه وارد همون جهت روند شده و روند معتبرتره؛
    اگر OI کاهشی باشد در حالی که قیمت در روند است، یعنی روند ضعیف/بدون تایید است.
    """

    url = FUTURES_BASE_URL + "/futures/data/openInterestHist"

    params = {"symbol": symbol, "period": period, "limit": lookback}

    response = requests.get(url, params=params)

    data = response.json()

    if not isinstance(data, list) or len(data) < 2:
        return 0.0

    data_sorted = sorted(data, key=lambda item: item["timestamp"])

    oldest = float(data_sorted[0]["sumOpenInterest"])
    newest = float(data_sorted[-1]["sumOpenInterest"])

    if oldest == 0:
        return 0.0

    return ((newest - oldest) / oldest) * 100


def get_fear_greed_index():

    """
    شاخص ترس و طمع کل بازار کریپتو (۰ تا ۱۰۰)، یک بار در هر اسکن گرفته می‌شود
    (نه به‌ازای هر ارز، چون این شاخص مربوط به کل بازار است نه یک ارز خاص).
    """

    response = requests.get(FEAR_GREED_API_URL, params={"limit": 1})

    data = response.json()

    return int(data["data"][0]["value"])


def _clamp(value, minimum, maximum):

    return max(minimum, min(value, maximum))


def calculate_fundamental_score(
    funding_rate_percent,
    oi_trend_percent,
    fear_greed_value,
    price_trend_up
):

    """
    امتیاز فاندامنتال از -100 (فرصت شارت قوی از دید فاندامنتال) تا +100
    (فرصت لانگ قوی)، حاصل جمع سه جزء:

    ۱) فاندینگ (خلاف‌جهت جمعیت، سقف ±30): فاندینگ خیلی مثبت (لانگ‌های شلوغ)
       امتیاز منفی می‌دهد (ریسک اصلاح به سمت پایین)، فاندینگ خیلی منفی امتیاز
       مثبت می‌دهد.

    ۲) روند Open Interest (تاییدی، سقف ±25): اگر OI هم‌جهت با روند قیمت رشد
       کند، روند را تایید و امتیاز را در همون جهت تقویت می‌کند؛ اگر OI کاهشی
       باشد، یعنی روند ضعیف است و امتیاز را کمی در جهت مخالف اصلاح می‌کند.

    ۳) ترس و طمع بازار (خلاف‌جهت جمعیت، سقف ±20): ترس شدید (نزدیک صفر) کمی
       به نفع لانگ، طمع شدید (نزدیک صد) کمی به نفع شارت است.

    این فقط یک وزن‌دهی قاعده‌محور و ساده است، نه یک مدل آماری دقیق؛ هدف این
    است که سیگنال تکنیکال را با زمینه‌ی بازار (سنتیمنت و پوزیشنینگ) تلطیف کند.
    """

    funding_score = _clamp(-funding_rate_percent * 600, -30, 30)

    if price_trend_up:
        oi_score = 25 if oi_trend_percent > 0 else -10
    else:
        oi_score = -25 if oi_trend_percent > 0 else 10

    fear_greed_value = fear_greed_value if fear_greed_value is not None else 50
    fear_greed_score = _clamp((50 - fear_greed_value) * 0.4, -20, 20)

    total = funding_score + oi_score + fear_greed_score

    return round(_clamp(total, -100, 100), 2)
