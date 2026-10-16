import random

import pytest

from src.futures import backtest, indicators, strategy
from src.futures.demo_data import synthetic_candles
from src.futures.futures_risk import build_trade_plan, net_reward_risk
from src.price_format import format_price, round_to_tick


# ---------------- prices with many decimals ----------------

@pytest.mark.parametrize("value, text", [
    (82072.9, "82,072.9"),
    (0.0000040879, "0.0000040879"),
    (4.0879e-06, "0.0000040879"),
    (0.00000000123, "0.0000000012"),
    (12.66340000, "12.6634"),
    (1.0, "1"),
    (None, "—"),
])
def test_format_price_shows_up_to_ten_decimals(value, text):
    assert format_price(value) == text


def test_round_to_tick():
    assert round_to_tick(82072.94, 0.1) == pytest.approx(82072.9)
    assert round_to_tick(82072.91, 0.1, "up") == pytest.approx(82073.0)
    assert round_to_tick(4.08794e-6, 1e-10) == pytest.approx(4.0879e-6)
    assert round_to_tick(4.08799e-6, 1e-10, "down") == pytest.approx(4.0879e-6)
    assert round_to_tick(0.123456789012, None) == pytest.approx(0.1234567890)


# ---------------- risk / reward ----------------

def test_reward_is_at_least_twice_the_risk_after_fees_for_any_input():
    rng = random.Random(7)
    for _ in range(2000):
        entry = 10 ** rng.uniform(-7, 5)
        tick = rng.choice([None, entry / 10**rng.randint(3, 6)])
        direction = rng.choice(["LONG", "SHORT"])
        distance = entry * rng.uniform(0.002, 0.08)
        stop = entry - distance if direction == "LONG" else entry + distance
        plan = build_trade_plan(direction, entry, stop, 200, 1, 5, 2.0, 0.06, tick)
        rr = net_reward_risk(direction, entry, plan["stop_loss_price"], plan["take_profit_price"], 0.0006)
        assert rr >= 2 - 1e-9, (direction, entry, tick, plan)
        assert plan["reward_risk_ratio"] >= 2


def test_position_size_risks_exactly_the_chosen_percent():
    plan = build_trade_plan("LONG", 100.0, 98.0, capital=1000, risk_percent=1, max_leverage=50)
    loss_per_unit = 2.0 + 0.0006 * (100 + 98)
    assert plan["position_size_usd"] / 100 * loss_per_unit == pytest.approx(10, rel=1e-3)


def test_stop_on_the_wrong_side_is_rejected():
    with pytest.raises(ValueError):
        build_trade_plan("LONG", 100.0, 101.0, 1000, 1, 5)


# ---------------- indicators ----------------

def test_wilder_rsi_and_atr_on_a_known_series():
    closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03,
              45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64]
    rsi = indicators.rsi(closes, 14)
    assert rsi[13] is None
    assert rsi[14] == pytest.approx(70.46, abs=0.05)     # the classic Wilder example
    assert rsi[19] == pytest.approx(57.92, abs=0.6)
    atr = indicators.atr([c + 1 for c in closes], [c - 1 for c in closes], closes, 14)
    assert atr[14] == pytest.approx(2.0)   # every true range is exactly 2 here


def test_ema_matches_definition():
    values = list(range(1, 31))
    out = indicators.ema(values, 10)
    assert out[9] == pytest.approx(5.5)
    assert out[10] == pytest.approx(11 * 2 / 11 + 5.5 * 9 / 11)


# ---------------- strategy ----------------

def test_textbook_setups_give_signals_and_a_flat_market_does_not():
    up = strategy.latest_signal(synthetic_candles("up"))
    down = strategy.latest_signal(synthetic_candles("down"))
    assert up["direction"] == "LONG" and up["stop"] < up["entry"]
    assert down["direction"] == "SHORT" and down["stop"] > down["entry"]
    assert strategy.latest_signal(synthetic_candles("flat")) is None


def test_crowded_funding_blocks_the_trade():
    candles = synthetic_candles("up")
    assert strategy.latest_signal(candles, funding_percent=0.01) is not None
    assert strategy.latest_signal(candles, funding_percent=0.08) is None
    assert strategy.latest_signal(synthetic_candles("down"), funding_percent=-0.08) is None


def test_too_little_history_gives_no_signal():
    assert strategy.latest_signal(synthetic_candles("up")[-200:]) is None


def test_no_lookahead_signal_does_not_change_when_the_future_is_known():
    candles = synthetic_candles("up", n=520)
    for i in range(300, 500, 7):
        alone = strategy.signal_at(strategy.compute_indicators(candles[:i + 1]), i)
        with_future = strategy.signal_at(strategy.compute_indicators(candles), i)
        assert alone == with_future, i


def test_four_hour_trend_uses_only_finished_four_hour_candles():
    candles = synthetic_candles("up", n=400)
    data = strategy.compute_indicators(candles)
    # changing the close of an unfinished 4h block must not change the 4h trend before it ends
    k = next(i for i in range(300, 400) if (candles[i][0] + 3_600_000) % 14_400_000 == 3_600_000)
    changed = [c[:] for c in candles]
    changed[k][4] *= 0.5
    assert strategy.compute_indicators(changed)["trend_4h"][k] == data["trend_4h"][k]


# ---------------- backtest ----------------

def _candles_after_signal(direction, path):
    """textbook setup, then the given future (list of (high, low) relative to entry)."""
    base = synthetic_candles(direction, n=500)
    entry = base[-1][4]
    t = base[-1][0]
    future = []
    for k, (high, low) in enumerate(path, start=1):
        future.append([t + k * 3_600_000, entry, entry * high, entry * low, entry, 100.0])
    return base + future


def test_backtest_counts_a_win_at_two_r():
    trades = backtest.backtest_symbol("T", _candles_after_signal("up", [(1.001, 0.999), (1.2, 0.999)]))
    last = trades[-1]
    assert last["result"] == "WIN" and last["r"] == pytest.approx(2.0, abs=0.02)


def test_backtest_assumes_the_stop_when_both_are_touched_in_one_candle():
    trades = backtest.backtest_symbol("T", _candles_after_signal("up", [(1.5, 0.5)]))
    assert trades[-1]["result"] == "LOSS" and trades[-1]["r"] == pytest.approx(-1.0, abs=0.01)


def test_backtest_short_and_timeout():
    trades = backtest.backtest_symbol("T", _candles_after_signal("down", [(1.001, 0.999)] * 5), max_hold=3)
    assert trades[-1]["direction"] == "SHORT" and trades[-1]["result"] == "TIMEOUT"
    assert -1 < trades[-1]["r"] < 0      # flat exit costs only the fees


def test_summary_math():
    trades = [
        {"result": "WIN", "r": 2.0, "closed": "1"},
        {"result": "LOSS", "r": -1.0, "closed": "2"},
        {"result": "LOSS", "r": -1.0, "closed": "3"},
        {"result": "TIMEOUT", "r": 0.5, "closed": "4"},
    ]
    s = backtest.summarize(trades)
    assert (s["trades"], s["wins"], s["losses"], s["timeouts"]) == (4, 1, 2, 1)
    assert s["win_rate"] == 25.0 and s["total_r"] == 0.5 and s["avg_r"] == 0.125
    assert s["profit_factor"] == 1.25 and s["max_drawdown_r"] == 2.0


def test_old_logic_still_runs_for_comparison():
    trades = backtest.backtest_symbol("T", synthetic_candles("up", n=600), "v1")
    assert isinstance(trades, list)
