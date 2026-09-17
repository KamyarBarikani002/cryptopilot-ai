"""
لایه ورود ساده تک‌کاربره برای پنل.

رمز عبور در جایی مثل کد یا گیت ذخیره نمی‌شه؛ فقط هش (PBKDF2) و سالت‌ش توی
فایل .env (که در .gitignore هست) یا توی متغیرهای محیطی سرور نگه داشته می‌شه.
برای ساختن این مقادیر از scripts/set_password.py استفاده کن.
"""

import hmac
import os

import streamlit as st
from dotenv import load_dotenv

from src.password_utils import hash_password

load_dotenv()


def _read_secret(name):

    """مقدار متغیر محیطی رو می‌خونه و فاصله‌های اضافه اول/آخرش رو حذف می‌کنه."""

    value = os.environ.get(name)

    if value is None:
        return None

    return value.strip()


def _password_is_configured() -> bool:

    return bool(_read_secret("APP_PASSWORD_HASH")) and bool(_read_secret("APP_PASSWORD_SALT"))


def _environment_report() -> str:

    """
    گزارش تشخیصی: نشون می‌ده برنامه کدوم متغیرها رو می‌بینه، بدون اینکه
    مقدارشون رو لو بده. برای وقتیه که متغیرها روی سرور تنظیم شدن ولی برنامه
    پیداشون نمی‌کنه.
    """

    lines = []

    for name in ("APP_PASSWORD_SALT", "APP_PASSWORD_HASH"):

        raw = os.environ.get(name)

        if raw is None:
            lines.append(name + ": NOT FOUND")
        elif not raw.strip():
            lines.append(name + ": EMPTY")
        else:
            lines.append(name + ": OK (" + str(len(raw.strip())) + " chars)")

    railway_count = len([key for key in os.environ if key.startswith("RAILWAY_")])
    app_count = len([key for key in os.environ if key.startswith("APP_")])

    lines.append("RAILWAY_* vars visible: " + str(railway_count))
    lines.append("APP_* vars visible: " + str(app_count))

    return "\n".join(lines)


def require_login():

    """
    اگر رمز هنوز تنظیم نشده، راهنما + گزارش تشخیصی نشون می‌ده و متوقف می‌شه.
    اگر تنظیم شده و کاربر لاگین نکرده، فرم ورود رو نشون می‌ده و متوقف می‌شه.
    اگر لاگین کرده، برمی‌گرده و بقیه پنل عادی رندر می‌شه.

    این تابع باید قبل از هر محتوای دیگه‌ای در صفحه صدا زده بشه.
    """

    if not _password_is_configured():

        st.set_page_config(page_title="تنظیم رمز عبور لازم است", page_icon="🔒")
        st.title("🔒 هنوز رمز عبوری تنظیم نشده")

        st.write(
            "اگر پنل رو روی کامپیوتر خودت اجرا می‌کنی، یک‌بار این دستور رو "
            "توی ترمینال بزن تا رمز ساخته بشه:"
        )
        st.code("python3 scripts/set_password.py", language="bash")

        st.write(
            "اگر پنل روی سرور (مثل Railway) اجرا می‌شه، این دو متغیر محیطی "
            "باید روی سرویس تنظیم شده باشن: APP_PASSWORD_SALT و "
            "APP_PASSWORD_HASH — همون مقادیری که اسکریپت بالا توی فایل .env "
            "نوشته."
        )

        with st.expander("🔍 برنامه الان چه چیزی می‌بیند؟ (برای عیب‌یابی)", expanded=True):
            st.code(_environment_report())
            st.caption(
                "اگر اینجا RAILWAY_* دیده می‌شود ولی APP_PASSWORD_* نه، یعنی "
                "متغیرها به این کانتینر نرسیده‌اند و باید سرویس دوباره دیپلوی شود."
            )

        st.stop()

    if st.session_state.get("authenticated"):
        return

    st.set_page_config(page_title="ورود به پنل", page_icon="🔒")
    st.title("🔒 ورود به CryptoPilot AI")

    with st.form("login_form"):

        password = st.text_input("رمز عبور", type="password")
        submitted = st.form_submit_button("ورود", type="primary", width='stretch')

    if submitted:

        salt = _read_secret("APP_PASSWORD_SALT")
        expected_hash = _read_secret("APP_PASSWORD_HASH")
        entered_hash = hash_password(password, salt)

        if hmac.compare_digest(entered_hash, expected_hash):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("رمز عبور اشتباه است.")

    st.stop()
