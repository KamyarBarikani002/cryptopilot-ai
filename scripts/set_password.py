#!/usr/bin/env python3
"""
تنظیم یا تغییر رمز عبور پنل.

این اسکریپت رو مستقیم توی ترمینال خودت اجرا کن (نه داخل چت با هوش مصنوعی)،
چون رمزی که اینجا وارد می‌کنی نباید جای دیگه‌ای ثبت بشه:

    python scripts/set_password.py

رمز رو با getpass می‌گیره (روی صفحه نمایش داده نمی‌شه)، هش PBKDF2 می‌کنه و
فقط هش + سالت رو توی فایل .env (کنار پروژه) می‌نویسه. فایل .env توی
.gitignore هست و هیچ‌وقت commit نمی‌شه.
"""

import getpass
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.password_utils import hash_password  # noqa: E402

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def _read_env_lines():

    if not os.path.exists(ENV_PATH):
        return []

    with open(ENV_PATH, "r") as file:
        return file.readlines()


def _write_env(lines, updates):

    keys_written = set()
    new_lines = []

    for line in lines:

        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue

        key = stripped.split("=", 1)[0]

        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            keys_written.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in keys_written:
            new_lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w") as file:
        file.writelines(new_lines)


def main():

    print("=== تنظیم رمز عبور پنل CryptoPilot AI ===")

    password = getpass.getpass("رمز عبور جدید را وارد کن: ")
    confirm = getpass.getpass("رمز عبور را دوباره وارد کن: ")

    if password != confirm:
        print("رمزها یکسان نبودند. دوباره اجرا کن.")
        return

    if len(password) < 6:
        print("رمز خیلی کوتاهه؛ حداقل ۶ کاراکتر بگذار.")
        return

    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)

    _write_env(
        _read_env_lines(),
        {
            "APP_PASSWORD_SALT": salt,
            "APP_PASSWORD_HASH": password_hash
        }
    )

    print(f"رمز عبور با موفقیت در {ENV_PATH} ذخیره شد.")
    print("حالا می‌تونی پنل رو با ./start_panel.sh اجرا کنی و با همین رمز وارد بشی.")


if __name__ == "__main__":
    main()
