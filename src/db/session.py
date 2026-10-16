"""
اتصال به دیتابیس و ساخت جدول‌ها (اگر وجود نداشته باشند).

- اگر متغیر محیطی DATABASE_URL تنظیم شده باشد (مثلاً یک Postgres رایگان روی
  Neon)، از همان استفاده می‌شود. این برای هاست‌هایی لازم است که دیسکشان با هر
  ری‌استارت پاک می‌شود (مثل پلن رایگان Render).
- در غیر این صورت، مثل قبل یک فایل SQLite در DATABASE_PATH ساخته می‌شود
  (اجرای لوکال روی مک، یا هاستی با volume دائمی).
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import DATABASE_PATH
from src.app_settings import read_setting
from src.db.models import Base


def _make_engine():

    url = read_setting("DATABASE_URL") or ""

    if url:

        # بعضی سرویس‌ها آدرس را با postgres:// می‌دهند که SQLAlchemy 2 نمی‌شناسد
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]

        # pool_pre_ping: دیتابیس‌های serverless (مثل Neon) بعد از چند دقیقه
        # بیکاری خاموش می‌شوند و اتصال‌های قبلی را قطع می‌کنند؛ این گزینه قبل از
        # هر استفاده اتصال را چک و در صورت نیاز عوض می‌کند.
        return create_engine(url, pool_pre_ping=True, pool_recycle=300)

    db_dir = os.path.dirname(DATABASE_PATH)

    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    return create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False})


engine = _make_engine()

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
