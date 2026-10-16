"""
نقطه‌ی مشترک همه‌ی درخواست‌ها به صرافی (کوکوین).

پاسخ‌های کوکوین همیشه این شکل را دارند: {"code": "200000", "data": ...}
اینجا سه حالت خطا به یک پیام روشن تبدیل می‌شوند، به‌جای اینکه کد بعدی با
داده‌ی غلط کار کند:
- HTTP 403/451: محدودیت منطقه‌ای (مثل اتفاقی که برای بایننس روی سرور آمریکا افتاد)
- code غیر از "200000": خطای خود کوکوین (پیامش نمایش داده می‌شود)
- خطای شبکه / timeout

نکته: برای نماد نامعتبر، کوکوین خطا نمی‌دهد و فقط "data": null برمی‌گرداند؛
این تابع data را همان‌طور برمی‌گرداند و فراخوان باید None را بررسی کند.
"""

import time

import requests

REQUEST_TIMEOUT_SECONDS = 15
KUCOIN_OK_CODE = "200000"


class ExchangeUnavailable(RuntimeError):
    """صرافی درخواست را رد کرد، خطا داد، یا جواب نداد."""


RETRY_STATUS = (429, 500, 502, 503, 504)
RETRY_WAITS_SECONDS = (1, 2, 4)


def kucoin_get(url, params=None):

    host = url.split("/")[2]

    # وقتی همه‌ی ارزهای کوکوین اسکن می‌شوند، گاهی کوکوین «درخواست زیاد» (429)
    # برمی‌گرداند؛ چند بار با مکث بیشتر دوباره تلاش می‌شود.
    for wait in RETRY_WAITS_SECONDS + (None,):

        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as error:
            if wait is not None:
                time.sleep(wait)
                continue
            raise ExchangeUnavailable(
                "اتصال به کوکوین برقرار نشد (" + type(error).__name__ + "، " + host + ")."
            ) from error

        if response.status_code in RETRY_STATUS and wait is not None:
            time.sleep(wait)
            continue

        break

    if response.status_code in (403, 451):
        raise ExchangeUnavailable(
            "کوکوین درخواست‌های این سرور را رد کرد (HTTP " + str(response.status_code)
            + "، " + host + ")؛ احتمالاً به‌خاطر محدودیت منطقه‌ای محل سرور."
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise ExchangeUnavailable(
            "پاسخ کوکوین قابل خواندن نبود (HTTP " + str(response.status_code) + "، " + host + ")."
        ) from error

    code = str(payload.get("code")) if isinstance(payload, dict) else None

    if response.status_code != 200 or code != KUCOIN_OK_CODE:
        message = payload.get("msg") if isinstance(payload, dict) else str(payload)[:200]
        raise ExchangeUnavailable(
            "کوکوین خطا برگرداند (HTTP " + str(response.status_code) + "، کد "
            + str(code) + "): " + str(message)
        )

    return payload.get("data")
