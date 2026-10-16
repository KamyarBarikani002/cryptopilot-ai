import pytest

from src.futures.portfolio_sim import simulate_account


def t(opened, closed, r):
    return {"opened": opened, "closed": closed, "r": r}


def test_compounding_and_monthly_returns():
    trades = [t("2026-01-05 10:00", "2026-01-05 12:00", 2.0),
              t("2026-02-05 10:00", "2026-02-05 12:00", 2.0),
              t("2026-03-05 10:00", "2026-03-05 12:00", -1.0)]
    out = simulate_account(trades, risk_percent=1, daily_loss_limit=1.5)
    assert out["final_equity"] == pytest.approx(100 * 1.02 * 1.02 * 0.99, abs=0.01)
    assert [m["return_percent"] for m in out["months"]] == [2.0, 2.0, -1.0]


def test_daily_loss_limit_blocks_new_trades_after_losses():
    # 0.5% risk: three losers fill the 1.5% day; the fourth (a winner) is not taken
    day = [t("2026-01-05 0%d:00" % h, "2026-01-05 0%d:30" % h, -1.0) for h in range(1, 4)]
    day.append(t("2026-01-05 05:00", "2026-01-05 06:00", 2.0))
    out = simulate_account(day, risk_percent=0.5, daily_loss_limit=1.5)
    assert out["taken"] == 3 and out["skipped_daily_limit"] == 1
    assert -1.5 <= out["worst_day_percent"] <= -1.45


def test_open_risk_counts_toward_the_day():
    # four overlapping trades at 0.5% risk: only three fit under 1.5% even before any loss
    trades = [t("2026-01-05 01:0%d" % k, "2026-01-05 09:00", -1.0) for k in range(4)]
    out = simulate_account(trades, risk_percent=0.5, daily_loss_limit=1.5, max_open=10)
    assert out["taken"] == 3
    assert out["worst_day_percent"] >= -1.5 - 1e-9


def test_new_day_resets_the_budget():
    trades = [t("2026-01-05 01:00", "2026-01-05 02:00", -1.0),
              t("2026-01-05 03:00", "2026-01-05 04:00", -1.0),
              t("2026-01-06 01:00", "2026-01-06 02:00", 2.0)]
    out = simulate_account(trades, risk_percent=1, daily_loss_limit=1.5)
    # day 1: a second 1% loser would exceed 1.5%, so it is skipped; day 2 starts fresh
    assert out["taken"] == 2 and out["skipped_daily_limit"] == 1


def test_max_open_positions():
    trades = [t("2026-01-05 01:0%d" % k, "2026-01-05 09:00", 1.0) for k in range(4)]
    out = simulate_account(trades, risk_percent=0.1, daily_loss_limit=1.5, max_open=2)
    assert out["taken"] == 2 and out["skipped_max_open"] == 2


def test_live_daily_budget():
    from src.futures.risk_budget import daily_budget
    history = [
        {"status": "LOSS", "closed_at": "2026-10-16 09:00:00"},
        {"status": "LOSS", "closed_at": "2026-10-15 09:00:00"},   # yesterday: does not count
        {"status": "WIN", "closed_at": "2026-10-16 10:00:00"},
        {"status": "OPEN", "closed_at": None},
    ]
    b = daily_budget(history, 0.5, 1.5, today="2026-10-16")
    assert (b["used_percent"], b["open_risk_percent"], b["remaining_percent"]) == (0.5, 0.5, 0.5)
    assert b["new_trades_allowed"] == 1 and b["max_trades_per_day"] == 3
    full = daily_budget(history + [{"status": "OPEN", "closed_at": None}], 0.5, 1.5, today="2026-10-16")
    assert full["new_trades_allowed"] == 0
