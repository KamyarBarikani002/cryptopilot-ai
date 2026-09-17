"""
مدل‌های SQLAlchemy برای وضعیت پایدار برنامه.

قبلاً همه این‌ها توی فایل‌های JSON زیر database/ ذخیره می‌شدند. حالا همه‌شون
توی یک دیتابیس SQLite واحد (database/cryptopilot.db) هستند تا هم پایدارتر
باشه (چند نوشتن هم‌زمان خراب نمی‌شه) و هم آماده باشه برای هاست‌شدن روی سرور.
"""

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, Float, String, Boolean, Text

Base = declarative_base()


class PanelSettings(Base):
    """تنظیمات نوار کناری پنل (تک ردیفی، id همیشه ۱)."""

    __tablename__ = "panel_settings"

    id = Column(Integer, primary_key=True)
    demo_mode = Column(Boolean, default=False)
    top_n = Column(Integer, default=30)
    capital = Column(Integer, default=200)
    auto_refresh_enabled = Column(Boolean, default=False)
    refresh_minutes = Column(Integer, default=15)


class PortfolioState(Base):
    """وضعیت کلی حساب DCA/پرتفوی نقطه‌ای (تک ردیفی، id همیشه ۱)."""

    __tablename__ = "portfolio_state"

    id = Column(Integer, primary_key=True)
    cash = Column(Float, default=0.0)
    total_contributed = Column(Float, default=0.0)
    last_contribution_period = Column(String, nullable=True)


class Holding(Base):
    """مقدار هر دارایی نگه‌داشته‌شده در پرتفوی DCA."""

    __tablename__ = "holdings"

    asset = Column(String, primary_key=True)
    units = Column(Float, default=0.0)


class Contribution(Base):
    """تاریخچه واریزهای ماهانه به پرتفوی DCA."""

    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String)
    amount = Column(Float)
    regime = Column(String)
    allocation_json = Column(Text)
    time = Column(String)


class SignalRecord(Base):
    """تاریخچه سیگنال‌های Long/Short اسکنر فیوچرز."""

    __tablename__ = "signal_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String)
    direction = Column(String)
    score = Column(Float, nullable=True)
    entry_price = Column(Float)
    stop_loss_price = Column(Float)
    take_profit_price = Column(Float)
    leverage = Column(Float, nullable=True)
    status = Column(String, default="OPEN")
    opened_at = Column(String)
    closed_at = Column(String, nullable=True)
    closed_price = Column(Float, nullable=True)
