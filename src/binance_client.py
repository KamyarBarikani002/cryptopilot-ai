"""
نقطه‌ی مشترک همه‌ی درخواست‌ها به بایننس.

دو دلیل برای وجود این فایل:

۱) بایننس از بعضی کشورها/دیتاسنترها (از جمله سرورهای آمریکا، مثل منطقه‌ی
   US West در Railway) درخواست‌ها را با کد HTTP 451 رد می‌کند و به‌جای داده،
   یک دیکشنری خطا برمی‌گرداند. کد قبلی آن دیکشنری را مثل لیست پیمایش می‌کرد و
   خطای گنگ "string indices must be integers" می‌داد. اینجا این حالت تشخیص
   داده می‌شود و یک پیام روشن بالا می‌رود.

۲) هیچ‌کدام از درخواست‌ها timeout نداشتند؛ اگر بایننس جواب نمی‌داد، پنل برای
   همیشه منتظر می‌ماند.
"""

import requests

REQUEST_TIMEOUT_SECONDS = 15


class BinanceUnavailable(RuntimeError):
    """بایننس درخواست را رد کرد (مثلاً به‌خاطر محدودیت منطقه‌ای) یا جواب نداد."""


def binance_get(url, params=None):

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as error:
        raise BinanceUnavailable(
            "اتصال به بایننس برقرار نشد (" + type(error).__name__ + "): " + url
        ) from error

    if response.status_code in (403, 451):
        raise BinanceUnavailable(
            "بایننس درخواست‌های این سرور را به‌خاطر محدودیت منطقه‌ای رد می‌کند "
            "(HTTP " + str(response.status_code) + "، " + url.split("/")[2] + "). "
            "سرور باید در منطقه‌ای خارج از آمریکا اجرا شود."
        )

    try:
        data = response.json()
    except ValueError as error:
        raise BinanceUnavailable(
            "پاسخ بایننس قابل خواندن نبود (HTTP " + str(response.status_code) + ")."
        ) from error

    if response.status_code != 200:
        message = data.get("msg") if isinstance(data, dict) else str(data)[:200]
        raise BinanceUnavailable(
            "بایننس خطا برگرداند (HTTP " + str(response.status_code) + "): " + str(message)
        )

    return data
