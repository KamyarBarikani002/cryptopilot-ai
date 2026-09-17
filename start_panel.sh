#!/bin/bash
# اجرای پنل با یک دستور: به پوشه پروژه می‌رود، وابستگی‌ها را نصب می‌کند
# (اگر قبلاً نصب نشده باشند) و پنل Streamlit را باز می‌کند.

cd "$(dirname "$0")" || exit 1

pip install -r requirements.txt

streamlit run dashboard.py
