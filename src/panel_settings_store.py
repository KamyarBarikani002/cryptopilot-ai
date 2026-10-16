"""
تنظیمات نوار کناری پنل (حالت آزمایشی، تعداد ارز، سرمایه، تازه‌سازی خودکار).

قبلاً توی database/panel_settings.json ذخیره می‌شد؛ حالا توی همون دیتابیس
SQLite بقیه وضعیت‌ها. تابع‌ها همون شکل قبلی (دیکشنری ساده) رو برمی‌گردونن.
"""

from config.settings import SCAN_TOP_N, INITIAL_CAPITAL
from src.db.session import SessionLocal
from src.db.models import PanelSettings

DEFAULT_PANEL_SETTINGS = {
    "demo_mode": False,
    "top_n": SCAN_TOP_N,
    "capital": int(INITIAL_CAPITAL),
    "auto_refresh_enabled": False,
    "refresh_minutes": 15,
    "risk_percent": 0.5,
    "daily_loss_limit": 1.5,
}


def load_panel_settings():

    session = SessionLocal()

    try:

        row = session.get(PanelSettings, 1)

        if row is None:
            return dict(DEFAULT_PANEL_SETTINGS)

        return {
            "demo_mode": bool(row.demo_mode),
            "top_n": row.top_n,
            "capital": row.capital,
            "auto_refresh_enabled": bool(row.auto_refresh_enabled),
            "refresh_minutes": row.refresh_minutes,
            "risk_percent": row.risk_percent if row.risk_percent is not None else DEFAULT_PANEL_SETTINGS["risk_percent"],
            "daily_loss_limit": (
                row.daily_loss_limit if row.daily_loss_limit is not None else DEFAULT_PANEL_SETTINGS["daily_loss_limit"]
            ),
        }

    finally:
        session.close()


def save_panel_settings(settings):

    session = SessionLocal()

    try:

        row = session.get(PanelSettings, 1)

        if row is None:
            row = PanelSettings(id=1)
            session.add(row)

        row.demo_mode = settings["demo_mode"]
        row.top_n = settings["top_n"]
        row.capital = settings["capital"]
        row.auto_refresh_enabled = settings["auto_refresh_enabled"]
        row.refresh_minutes = settings["refresh_minutes"]
        row.risk_percent = settings.get("risk_percent", DEFAULT_PANEL_SETTINGS["risk_percent"])
        row.daily_loss_limit = settings.get("daily_loss_limit", DEFAULT_PANEL_SETTINGS["daily_loss_limit"])

        session.commit()

    finally:
        session.close()
