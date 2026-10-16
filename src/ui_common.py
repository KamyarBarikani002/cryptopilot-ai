"""بخش‌های مشترک رابط کاربری که در همه‌ی صفحه‌های پنل نشان داده می‌شوند."""

import streamlit as st

from src.db.session import engine


def render_storage_status():

    """
    در نوار کناری نشان می‌دهد داده‌ها (پرتفوی، تاریخچه‌ی سیگنال‌ها، تنظیمات)
    کجا ذخیره می‌شوند. روی Streamlit Cloud فایل SQLite با هر ری‌استارت یا دیپلوی
    پاک می‌شود، پس این هشدار تا وقتی DATABASE_URL تنظیم نشده دیده می‌شود.
    """

    if engine.dialect.name == "postgresql":
        st.sidebar.caption("🗄️ داده‌ها در دیتابیس دائمی (Postgres) ذخیره می‌شوند.")
    else:
        st.sidebar.warning(
            "⚠️ داده‌ها در فایل SQLite همین سرور ذخیره می‌شوند. روی Streamlit "
            "Cloud این فایل با هر ری‌استارت یا دیپلوی پاک می‌شود. برای دائمی "
            "شدن، DATABASE_URL را در Secrets تنظیم کن."
        )
