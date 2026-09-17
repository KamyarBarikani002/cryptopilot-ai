"""
تابع هش کردن رمز عبور، جدا از src/auth.py.

اینجا نگه‌داشته می‌شه (به‌جای src/auth.py) چون src/auth.py خودش streamlit رو
ایمپورت می‌کنه، ولی scripts/set_password.py فقط برای هش کردن رمز اجرا می‌شه و
نباید مجبور باشه streamlit نصب باشه (مخصوصاً وقتی هنوز pip install کامل نزدی،
یا داری فقط رمز رو روی یه سرور تنظیم می‌کنی).
"""

import hashlib

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str, salt: str) -> str:

    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS
    ).hex()
