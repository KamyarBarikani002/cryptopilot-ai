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

from src.app_settings import locate_setting, read_setting, streamlit_secret_names
from src import remember_me
from src.password_utils import hash_password

load_dotenv()


def _read_secret(name):

    return read_setting(name)


def _password_is_configured() -> bool:

    return bool(_read_secret("APP_PASSWORD_HASH")) and bool(_read_secret("APP_PASSWORD_SALT"))


def _environment_report() -> str:

    """
    گزارش تشخیصی: نشون می‌ده برنامه هر مقدار رو از کجا پیدا کرده (یا نکرده)،
    بدون اینکه خود مقدار رو لو بده.
    """

    lines = []

    for name in ("APP_PASSWORD_SALT", "APP_PASSWORD_HASH"):

        value, source = locate_setting(name)

        if value is None:
            lines.append(name + ": NOT FOUND")
        elif not value:
            lines.append(name + ": EMPTY (in " + source + ")")
        else:
            lines.append(name + ": OK, " + str(len(value)) + " chars, from " + source)

    secret_names = streamlit_secret_names()

    if secret_names is None:
        lines.append("Streamlit Secrets: none defined")
    else:
        lines.append("Streamlit Secrets keys: " + (", ".join(repr(n) for n in secret_names) or "(empty)"))

    lines.append("RAILWAY_* env vars: " + str(len([k for k in os.environ if k.startswith("RAILWAY_")])))
    lines.append("APP_* env vars: " + str(len([k for k in os.environ if k.strip().startswith("APP_")])))

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
            "اگر پنل روی Streamlit Community Cloud اجرا می‌شه: Manage app → "
            "Settings → Secrets و این دو خط رو با مقادیر خودت ذخیره کن (بعدش "
            "اپ خودش ری‌استارت می‌شه):"
        )
        st.code(
            'APP_PASSWORD_SALT = "..."\nAPP_PASSWORD_HASH = "..."',
            language="toml"
        )

        st.write(
            "روی هاست‌های دیگه (Railway، Render، Docker) همین دو اسم رو به‌عنوان "
            "متغیر محیطی تعریف کن."
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

    # «مرا به خاطر بسپار»: اگر مرورگر توکن معتبر دارد، بدون رمز وارد شو.
    # بعد از «خروج» در همین نشست، کوکی قدیمی (که Streamlit فقط یک‌بار در شروع
    # نشست می‌خواند) دیگر قبول نمی‌شود.
    st.set_page_config(page_title="ورود به پنل", page_icon="🔒")

    if not st.session_state.get("logged_out"):

        token = remember_me.read_cookie() or remember_me.read_cookie_via_browser()

        if remember_me.token_is_valid(token, _read_secret("APP_PASSWORD_HASH")):
            st.session_state.authenticated = True
            st.rerun()   # صفحه از اول، بدون کامپوننت خواندن کوکی

    st.title("🔒 ورود به CryptoPilot AI")

    if st.session_state.pop("clear_cookie", False):
        remember_me.clear_cookie()

    with st.form("login_form"):

        password = st.text_input("رمز عبور", type="password")
        remember = st.checkbox(
            "مرا به خاطر بسپار (" + str(remember_me.REMEMBER_DAYS) + " روز)", value=True,
            help="روی کامپیوتر یا گوشی مشترک تیک این گزینه را بردار.",
        )
        submitted = st.form_submit_button("ورود", type="primary", width='stretch')

    if submitted:

        salt = _read_secret("APP_PASSWORD_SALT")
        expected_hash = _read_secret("APP_PASSWORD_HASH")
        entered_hash = hash_password(password, salt)

        if hmac.compare_digest(entered_hash, expected_hash):
            st.session_state.authenticated = True
            if remember:
                st.session_state.pending_cookie = remember_me.make_token(expected_hash)
            st.rerun()
        else:
            st.error("رمز عبور اشتباه است.")

    st.stop()


def _logout():

    st.session_state.authenticated = False
    st.session_state.logged_out = True
    st.session_state.clear_cookie = True
    st.session_state.pop("pending_cookie", None)


def render_account_controls():

    """
    دکمه‌ی خروج در نوار کناری، و نوشتن کوکی «مرا به خاطر بسپار» بعد از ورود.
    هر صفحه بعد از require_login این را صدا می‌زند.
    """

    token = st.session_state.pop("pending_cookie", None)

    with st.sidebar:

        if token:
            remember_me.write_cookie(token)

        st.button("🚪 خروج", on_click=_logout, width='stretch')
