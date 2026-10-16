"""
بک‌تست سیگنال‌های فیوچرز روی کندل‌های واقعی گذشته.

برای هر ارز، کندل به کندل جلو می‌رود و دقیقاً همان تابعی را صدا می‌زند که
اسکنر زنده صدا می‌زند (فقط با داده‌ی تا همان لحظه). اگر سیگنال آمد:
- ورود روی قیمت بسته‌شدن همان کندل،
- حد ضرر/حد سود از build_trade_plan (حداقل ۱ به ۲ بعد از کارمزد)،
- خروج وقتی قیمت به یکی برسد. اگر در یک کندل هر دو لمس شوند، بدبینانه
  «حد ضرر» حساب می‌شود (چون ترتیب داخل کندل معلوم نیست).
- اگر بعد از max_hold کندل به هیچ‌کدام نرسید، با قیمت بسته‌شدن آن کندل خارج
  می‌شود (TIMEOUT).
هر ارز در هر لحظه حداکثر یک پوزیشن دارد.

نتیجه‌ها به واحد R گزارش می‌شوند: ۱R یعنی همان مقداری که با خوردن حد ضرر از
دست می‌رود (با کارمزد). برد کامل با ۱ به ۲ یعنی حدود +2R.
"""

import bisect
from datetime import datetime, timezone

from src.futures import strategy
from src.futures.futures_risk import _loss_per_unit, build_trade_plan


# نام‌های قدیمی (v1 = منطق قبلی، v2 = پولبک) برای سازگاری نگه داشته شده‌اند
STRATEGIES = {
    "dip": strategy.dip_signal_at,
    "pullback": strategy.signal_at,
    "v1": strategy.dip_signal_at,
    "v2": strategy.signal_at,
    "breakout": strategy.breakout_signal_at,
}

_WARMUP = {"dip": strategy.DIP_MIN_CANDLES, "v1": strategy.DIP_MIN_CANDLES,
           "pullback": strategy.MIN_CANDLES, "v2": strategy.MIN_CANDLES,
           "breakout": strategy.BREAKOUT_MIN_CANDLES}


def _funding_lookup(funding_points):

    """funding_points: [(time_ms, percent), ...] -> تابع «آخرین فاندینگ تا لحظه‌ی t»."""

    if not funding_points:
        return lambda t: None

    points = sorted(funding_points)
    times = [p[0] for p in points]

    def lookup(t):
        k = bisect.bisect_right(times, t) - 1
        return points[k][1] if k >= 0 else None

    return lookup


def backtest_symbol(
    symbol,
    candles,
    strategy_name="v2",
    params=None,
    funding_points=None,
    min_reward_risk=2.0,
    fee_percent=0.06,
    max_hold=72,
    tick_size=None,
):

    signal_fn = STRATEGIES[strategy_name]
    data = strategy.compute_indicators(candles)
    funding_at = _funding_lookup(funding_points)
    fee_rate = fee_percent / 100

    trades = []
    n = len(candles)
    i = _WARMUP[strategy_name]

    while i < n - 1:

        signal = signal_fn(data, i, funding_at(data["time"][i]), params)

        if signal is None:
            i += 1
            continue

        try:
            plan = build_trade_plan(
                signal["direction"], signal["entry"], signal["stop"],
                capital=1000, risk_percent=1, max_leverage=5,
                min_reward_risk=min_reward_risk, fee_percent=fee_percent, tick_size=tick_size,
            )
        except ValueError:
            i += 1
            continue

        entry, stop, target = plan["entry_price"], plan["stop_loss_price"], plan["take_profit_price"]
        long_ = signal["direction"] == "LONG"
        loss_unit = _loss_per_unit(entry, stop, fee_rate)

        result, exit_price, j = "TIMEOUT", None, i

        for j in range(i + 1, min(i + 1 + max_hold, n)):
            hit_stop = data["low"][j] <= stop if long_ else data["high"][j] >= stop
            hit_target = data["high"][j] >= target if long_ else data["low"][j] <= target
            if hit_stop:
                result, exit_price = "LOSS", stop
                break
            if hit_target:
                result, exit_price = "WIN", target
                break

        if exit_price is None:
            exit_price = data["close"][j]

        move = (exit_price - entry) if long_ else (entry - exit_price)
        r = (move - fee_rate * (entry + exit_price)) / loss_unit

        trades.append({
            "symbol": symbol,
            "direction": signal["direction"],
            "opened": _iso(data["time"][i]),
            "closed": _iso(data["time"][j]),
            "result": result,
            "r": round(r, 3),
            "entry": entry,
            "stop": stop,
            "target": target,
            "bars": j - i,
            "strength": signal.get("strength"),
        })

        i = j + 1

    return trades


def _iso(time_ms):

    return datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def split_halves(trades, middle_iso):

    """معاملات نیمه‌ی اول و دوم دوره، برای دیدن اینکه نتیجه پایدار است یا شانسی."""

    first = [t for t in trades if t["opened"] < middle_iso]
    second = [t for t in trades if t["opened"] >= middle_iso]
    return first, second


def summarize(trades):

    total = len(trades)

    if total == 0:
        return {"trades": 0, "wins": 0, "losses": 0, "timeouts": 0, "win_rate": 0.0,
                "avg_r": 0.0, "total_r": 0.0, "profit_factor": 0.0, "max_drawdown_r": 0.0}

    wins = sum(1 for t in trades if t["result"] == "WIN")
    losses = sum(1 for t in trades if t["result"] == "LOSS")
    gross_win = sum(t["r"] for t in trades if t["r"] > 0)
    gross_loss = -sum(t["r"] for t in trades if t["r"] < 0)

    equity = peak = drawdown = 0.0
    for t in sorted(trades, key=lambda t: t["closed"]):
        equity += t["r"]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)

    total_r = sum(t["r"] for t in trades)

    return {
        "trades": total,
        "wins": wins,
        "losses": losses,
        "timeouts": total - wins - losses,
        "win_rate": round(wins / total * 100, 1),
        "avg_r": round(total_r / total, 3),
        "total_r": round(total_r, 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else float("inf"),
        "max_drawdown_r": round(drawdown, 2),
    }


def equity_curve(trades):

    points, equity = [], 0.0

    for t in sorted(trades, key=lambda t: t["closed"]):
        equity += t["r"]
        points.append({"time": t["closed"], "equity_r": round(equity, 2)})

    return points
