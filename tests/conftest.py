import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# کد پروژه با import های مطلق مثل "from src.x import y" نوشته شده و صفحه‌های
# استریم‌لیت با مسیر نسبی (dashboard.py) باز می‌شوند، پس تست‌ها از ریشه اجرا می‌شوند.
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
