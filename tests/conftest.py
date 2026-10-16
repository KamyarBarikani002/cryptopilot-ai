import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# کد پروژه با import های مطلق مثل "from src.x import y" نوشته شده و صفحه‌های
# استریم‌لیت با مسیر نسبی (dashboard.py) باز می‌شوند، پس تست‌ها از ریشه اجرا می‌شوند.
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_retry_waits(monkeypatch):
    # retries on KuCoin rate limits still happen in tests, just without sleeping
    monkeypatch.setattr("src.exchange_client.RETRY_WAITS_SECONDS", (0, 0, 0))
