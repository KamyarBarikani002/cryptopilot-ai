"""
شبیه‌سازی حساب واقعی با قانون‌های مدیریت سرمایه، روی معاملات بک‌تست.

بک‌تست هر ارز را جدا حساب می‌کند (به واحد R). اینجا همه‌ی معاملات همه‌ی ارزها
روی یک حساب مشترک و به ترتیب زمان اجرا می‌شوند:

- ریسک هر معامله = risk_percent درصد از سرمایه‌ی همان لحظه (سود مرکب).
- سقف ضرر روزانه: در هر روز (UTC) مجموع «زیان قطعی امروز + ریسک پوزیشن‌های باز»
  هیچ‌وقت از daily_loss_limit درصد سرمایه‌ی اول همان روز بیشتر نمی‌شود. اگر
  معامله‌ی تازه این سقف را رد کند، گرفته نمی‌شود. یعنی حتی اگر همه‌ی پوزیشن‌های
  باز همان روز حد ضرر بخورند، زیان روز از سقف بیشتر نمی‌شود.
- حداکثر تعداد پوزیشن باز همزمان (max_open).
"""

from collections import defaultdict


def _day(iso):
    return iso[:10]


def _month(iso):
    return iso[:7]


def simulate_account(trades, risk_percent=0.5, daily_loss_limit=1.5, max_open=5, start_equity=100.0):

    events = []
    for k, t in enumerate(trades):
        events.append((t["opened"], 1, k))
        events.append((t["closed"], 0, k))   # بستن قبل از باز کردن در همان دقیقه

    events.sort()

    equity = start_equity
    open_risk = {}               # k -> مقدار ریسک (واحد پول)
    day = None
    day_start_equity = equity
    day_realized = 0.0
    taken, skipped_limit, skipped_slots = [], 0, 0

    month_start = {}
    month_end = {}
    day_pnl = defaultdict(float)
    day_start = {}
    peak = equity
    max_drawdown = 0.0

    for when, kind, k in events:

        today = _day(when)

        if today != day:
            day = today
            day_start_equity = equity
            day_realized = 0.0
            day_start.setdefault(today, equity)

        month_start.setdefault(_month(when), equity)

        if kind == 0:
            if k not in open_risk:
                continue
            risk_amount = open_risk.pop(k)
            pnl = trades[k]["r"] * risk_amount
            equity += pnl
            day_realized += pnl
            day_pnl[today] += pnl
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)
            month_end[_month(when)] = equity
            continue

        if len(open_risk) >= max_open:
            skipped_slots += 1
            continue

        risk_amount = equity * risk_percent / 100
        limit_amount = day_start_equity * daily_loss_limit / 100
        worst_case_today = -min(day_realized, 0.0) + sum(open_risk.values()) + risk_amount

        if worst_case_today > limit_amount + 1e-12:
            skipped_limit += 1
            continue

        open_risk[k] = risk_amount
        taken.append(trades[k])

    months = []
    running = start_equity
    for month in sorted(set(month_start) | set(month_end)):
        begin = month_start.get(month, running)
        end = month_end.get(month, begin)
        months.append({"month": month, "return_percent": round((end - begin) / begin * 100, 2)})
        running = end

    worst_day = min(
        ((pnl / day_start[d]) * 100 for d, pnl in day_pnl.items()), default=0.0
    )

    full_months = months[1:-1] if len(months) > 2 else months   # ماه اول و آخر ناقص‌اند
    monthly = [m["return_percent"] for m in full_months]

    return {
        "final_equity": round(equity, 2),
        "total_return_percent": round((equity - start_equity) / start_equity * 100, 2),
        "months": months,
        "avg_month_percent": round(sum(monthly) / len(monthly), 2) if monthly else 0.0,
        "months_at_least_10": sum(1 for m in monthly if m >= 10),
        "full_months": len(monthly),
        "worst_month_percent": min(monthly) if monthly else 0.0,
        "worst_day_percent": round(worst_day, 2),
        "max_drawdown_percent": round(max_drawdown, 2),
        "taken": len(taken),
        "skipped_daily_limit": skipped_limit,
        "skipped_max_open": skipped_slots,
    }
