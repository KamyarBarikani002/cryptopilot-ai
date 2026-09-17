"""
وضعیت پایدار حساب DCA/پرتفوی نقطه‌ای.

قبلاً این فایل مستقیم روی database/portfolio_state.json کار می‌کرد. حالا
پشت‌صحنه از دیتابیس SQLite استفاده می‌کنه، ولی load_state()/save_state()
دقیقاً همون دیکشنری قبلی رو می‌دن/می‌گیرن تا بقیه کد (مثل src/core/account.py)
لازم نباشه تغییر کنه.

اگر فایل JSON قدیمی وجود داشته باشه و دیتابیس هنوز خالی باشه، اولین بار که
load_state() صدا زده بشه، داده‌های قدیمی خودکار به دیتابیس منتقل می‌شن.
"""

import json
import os

from config.settings import INITIAL_CAPITAL, PORTFOLIO_STATE_PATH
from src.db.session import SessionLocal
from src.db.models import PortfolioState as PortfolioStateRow, Holding, Contribution


def _default_state():

    return {
        "cash": INITIAL_CAPITAL,
        "holdings": {},
        "total_contributed": INITIAL_CAPITAL,
        "last_contribution_period": None,
        "contributions": []
    }


def _migrate_legacy_json_if_needed(session):

    already_has_data = session.get(PortfolioStateRow, 1) is not None

    if already_has_data or not os.path.exists(PORTFOLIO_STATE_PATH):
        return

    with open(PORTFOLIO_STATE_PATH, "r") as file:
        legacy = json.load(file)

    session.add(PortfolioStateRow(
        id=1,
        cash=legacy.get("cash", INITIAL_CAPITAL),
        total_contributed=legacy.get("total_contributed", INITIAL_CAPITAL),
        last_contribution_period=legacy.get("last_contribution_period")
    ))

    for asset, units in legacy.get("holdings", {}).items():
        session.add(Holding(asset=asset, units=units))

    for contribution in legacy.get("contributions", []):
        session.add(Contribution(
            period=contribution.get("period"),
            amount=contribution.get("amount"),
            regime=contribution.get("regime"),
            allocation_json=json.dumps(contribution.get("allocation", {})),
            time=contribution.get("time")
        ))

    session.commit()


def load_state():

    session = SessionLocal()

    try:

        _migrate_legacy_json_if_needed(session)

        row = session.get(PortfolioStateRow, 1)

        if row is None:
            defaults = _default_state()
            row = PortfolioStateRow(
                id=1,
                cash=defaults["cash"],
                total_contributed=defaults["total_contributed"],
                last_contribution_period=defaults["last_contribution_period"]
            )
            session.add(row)
            session.commit()

        holdings = {h.asset: h.units for h in session.query(Holding).all()}

        contributions = []

        for c in session.query(Contribution).order_by(Contribution.id).all():
            contributions.append({
                "period": c.period,
                "amount": c.amount,
                "regime": c.regime,
                "allocation": json.loads(c.allocation_json) if c.allocation_json else {},
                "time": c.time
            })

        return {
            "cash": row.cash,
            "holdings": holdings,
            "total_contributed": row.total_contributed,
            "last_contribution_period": row.last_contribution_period,
            "contributions": contributions
        }

    finally:
        session.close()


def save_state(state):

    session = SessionLocal()

    try:

        row = session.get(PortfolioStateRow, 1)

        if row is None:
            row = PortfolioStateRow(id=1)
            session.add(row)

        row.cash = state["cash"]
        row.total_contributed = state["total_contributed"]
        row.last_contribution_period = state["last_contribution_period"]

        # ساده‌ترین راه درست برای sync کردن holdings: پاک کردن و دوباره نوشتن
        session.query(Holding).delete()

        for asset, units in state["holdings"].items():
            session.add(Holding(asset=asset, units=units))

        # فقط واریزهای جدید (که هنوز توی دیتابیس نیستن) رو اضافه می‌کنیم
        existing_count = session.query(Contribution).count()
        new_contributions = state["contributions"][existing_count:]

        for contribution in new_contributions:
            session.add(Contribution(
                period=contribution["period"],
                amount=contribution["amount"],
                regime=contribution["regime"],
                allocation_json=json.dumps(contribution["allocation"]),
                time=contribution["time"]
            ))

        session.commit()

    finally:
        session.close()
