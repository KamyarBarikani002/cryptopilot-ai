# صفحه‌ی ساده برای تست ورود (test_remember_me.py)؛ جزو پنل نیست.
from src.auth import render_account_controls, require_login

require_login()

import streamlit as st  # noqa: E402

st.write("PANEL CONTENT")
render_account_controls()
