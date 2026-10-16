"""
خواندن تنظیمات محرمانه (رمز پنل، آدرس دیتابیس) از هر جایی که هاست گذاشته باشد.

هاست‌ها این مقادیر را جاهای مختلفی می‌گذارند:
- Railway / Render / Docker: متغیر محیطی
- اجرای لوکال: فایل .env (که load_dotenv در auth.py به متغیر محیطی تبدیلش می‌کند)
- Streamlit Community Cloud: بخش Secrets که از طریق st.secrets خوانده می‌شود
  (روی Streamlit Cloud تست شد: این مقادیر به متغیر محیطی تبدیل نشدند)

ترتیب جست‌وجو: متغیر محیطی با اسم دقیق، متغیر محیطی با اسمی که فاصله‌ی اضافه
دارد (باگ واقعی Railway: "APP_PASSWORD_SALT ")، و در آخر st.secrets.
"""

import os


def _from_environment(name):

    value = os.environ.get(name)

    if value is not None:
        return value, "environment"

    for key, candidate in os.environ.items():
        if key.strip() == name:
            return candidate, "environment (variable NAME has extra whitespace)"

    return None, None


def streamlit_secret_names():

    """اسم کلیدهای st.secrets، یا None اگر اصلاً Secrets تعریف نشده باشد."""

    try:
        import streamlit as st
        return [str(key) for key in st.secrets.keys()]
    except Exception:
        return None


def _from_streamlit_secrets(name):

    try:
        import streamlit as st
        secrets = st.secrets
        keys = list(secrets.keys())
    except Exception:
        return None, None

    for key in keys:

        if str(key).strip() != name:
            continue

        value = secrets[key]

        if isinstance(value, (str, int, float)):
            source = "st.secrets" if str(key) == name else "st.secrets (key has extra whitespace)"
            return str(value), source

    return None, None


def locate_setting(name):

    """(مقدار بدون فاصله‌های اول/آخر، منبع) یا (None, None)."""

    for finder in (_from_environment, _from_streamlit_secrets):

        value, source = finder(name)

        if value is not None:
            return value.strip(), source

    return None, None


def read_setting(name):

    return locate_setting(name)[0]
