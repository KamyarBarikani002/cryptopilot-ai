"""
اتصال به دیتابیس SQLite و ساخت جدول‌ها (اگر وجود نداشته باشند).

مسیر فایل دیتابیس از config/settings.py (DATABASE_PATH) خونده می‌شه، همون
مسیری که قبلاً برای دیتابیس در نظر گرفته شده بود ولی استفاده نمی‌شد.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import DATABASE_PATH
from src.db.models import Base

_db_dir = os.path.dirname(DATABASE_PATH)

if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

engine = create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False})

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)
