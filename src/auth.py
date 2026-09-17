"""
لایه ورود ساده تک‌کاربره برای پنل.

رمز عبور در جایی مثل کد یا گیت ذخیره نمی‌شه؛ فقط هش (PBKDF2) و سالت‌ش توی
فایل .env (که در .gitignore هست) نگه داشته می‌شه. برای تنظیم یا تغییر رمز از
scripts/set_password.py استفاده کن.
"""

import hashlib
import hmac
import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str, salt: str) -> str:

    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS
    ).hex()


def _password_is_configured() -> bool:

    return bool(os.environ.get("APP_PASSWORD_HASH")) and bool(os.environ.get("APP_PASSWORD_SALT"))


def require_login():

    """
    اگر رمز هنوز توی .env تنظیم نشده، یک راهنما نشون می‌ده و متوقف می‌شه.
    اگر تنظیم شده و کاربر لاگین نکرده، فرم ورود رو نشون می‌ده و متوقف می‌شه.
    اگر لاگین کرده، به‌سادگی برمی‌گرده و بقیه پنل عادی رندر می‌شه.

    این تابع باید اولین خط dashboard.py صدا زده بشه، قبل از هر محتوای دیگه.
    """

    if not _password_is_configured():

        st.set_page_config(page_title="تنظیم رمز عبور لازم است", page_icon="🔒")
        st.title("🔒 هنوز رمز عبوری تنظیم نشده")
        st.write(
            "قبل از استفاده از پنل، یک‌بار توی ترمینال خودت (نه توی چت) این "
            "دستور رو اجرا کن تا رمز عبور پنل رو تنظیم کنی:"
        )
        st.code("python scripts/set_password.py", language="bash")
        st.caption(
            "این اسکریپت رمز رو می‌پرسه و فقط هش‌شده‌ش رو توی فایل .env "
            "(که وارد گیت نمی‌شه) ذخیره می‌کنه."
        )
        st.stop()

    if st.session_state.get("authenticated"):
        return

    st.set_page_config(page_title="ورود به پنل", page_icon="🔒")
    st.title("🔒 ورود به CryptoPilot AI")

    with st.form("login_form"):

        password = st.text_input("رمز عبور", type="password")
        submitted = st.form_submit_button("ورود", type="primary", use_container_width=True)

    if submitted:

        salt = os.environ["APP_PASSWORD_SALT"]
        expected_hash = os.environ["APP_PASSWORD_HASH"]
        entered_hash = hash_password(password, salt)

        if hmac.compare_digest(entered_hash, expected_hash):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("رمز عبور اشتباه است.")

    st.stop()
