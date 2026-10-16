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


def _add_missing_columns():

    """
    create_all جدول‌های جدید را می‌سازد ولی به جدول‌هایی که از قبل وجود دارند
    ستون اضافه نمی‌کند. دیتابیس روی سرور از نسخه‌های قبلی آمده، پس ستون‌های
    تازه‌ی مدل‌ها را اینجا با ALTER TABLE اضافه می‌کنیم (هم SQLite هم Postgres).
    """

    from sqlalchemy import inspect, text

    inspector = inspect(engine)

    for table in Base.metadata.sorted_tables:

        if not inspector.has_table(table.name):
            continue

        existing = {column["name"] for column in inspector.get_columns(table.name)}

        for column in table.columns:

            if column.name in existing:
                continue

            column_type = column.type.compile(dialect=engine.dialect)

            with engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE " + table.name + " ADD COLUMN " + column.name + " " + column_type
                ))


_add_missing_columns()

SessionLocal = sessionmaker(bind=engine)
