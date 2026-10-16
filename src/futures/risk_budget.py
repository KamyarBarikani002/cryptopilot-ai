"""
سقف ضرر روزانه برای اسکنر زنده.

فرض: هر سیگنالی که پنل ثبت کرده، معامله شده است (پنل معاملات واقعی تو را
نمی‌بیند). پس:
- زیان امروز = تعداد سیگنال‌هایی که امروز با حد ضرر بسته شده‌اند × ریسک هر معامله
- ریسک باز = تعداد سیگنال‌های باز × ریسک هر معامله
و تا وقتی «زیان امروز + ریسک باز + ریسک معامله‌ی تازه» از سقف روزانه بیشتر
نشود، معامله‌ی تازه مجاز است. «امروز» به وقت سرور (UTC) است.
"""

import math
from datetime import datetime


def daily_budget(history, risk_percent, daily_loss_limit, today=None):

    today = today or datetime.now().date().isoformat()

    losses_today = sum(
        1 for r in history
        if r["status"] == "LOSS" and (r.get("closed_at") or "")[:10] == today
    )
    open_count = sum(1 for r in history if r["status"] == "OPEN")

    used = losses_today * risk_percent
    at_risk = open_count * risk_percent
    remaining = max(daily_loss_limit - used - at_risk, 0.0)

    return {
        "losses_today": losses_today,
        "open_count": open_count,
        "used_percent": round(used, 2),
        "open_risk_percent": round(at_risk, 2),
        "remaining_percent": round(remaining, 2),
        "new_trades_allowed": int(math.floor(remaining / risk_percent + 1e-9)) if risk_percent > 0 else 0,
        "max_trades_per_day": int(math.floor(daily_loss_limit / risk_percent + 1e-9)) if risk_percent > 0 else 0,
    }
