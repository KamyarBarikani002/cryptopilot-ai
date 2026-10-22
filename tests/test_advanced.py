"""
تست‌های تحلیل تکنیکال پیشرفته، مدیریت خروج (سر‌به‌سر)، هم‌گرایی و اخبار.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.futures import exits, strategy
from src.futures import ta_advanced as ta


# ---------------------------------------------------------------- اندیکاتورها

def test_macd_bollinger_stochastic_obv_shapes_and_values():
    closes = [100 + i for i in range(60)]
    m = ta.macd(closes)
    assert m["macd"][-1] > 0 and m["macd_signal"][-1] is not None
    b = ta.bollinger(closes)
    assert b["bb_upper"][-1] > b["bb_mid"][-1] > b["bb_lower"][-1]
    assert b["bb_percent"][-1] > 0.5           # روند صعودی: نزدیک باند بالا
    s = ta.stochastic([c + 1 for c in closes], [c - 1 for c in closes], closes)
    assert s["stoch_k"][-1] > 80
    assert ta.obv([1, 2, 1, 1], [10, 20, 30, 40]) == [0.0, 20.0, -10.0, -10.0]


def test_swing_points_are_only_known_after_confirmation():
    highs = [1, 2, 3, 9, 3, 2, 1, 2, 3]
    lows = [h - 0.5 for h in highs]
    swing_highs, _ = ta.swing_points(highs, lows, k=3)
    assert [(j, p) for j, p, _ in swing_highs] == [(3, 9)]
    assert ta.known_swings(swing_highs, 5) == []          # هنوز قطعی نشده (بدون نگاه به آینده)
    assert len(ta.known_swings(swing_highs, 6)) == 1


def test_nearest_levels_and_market_structure():
    swing_highs = ta.Swings([(10, 110.0, 13), (30, 120.0, 33)])
    swing_lows = ta.Swings([(20, 100.0, 23), (40, 105.0, 43)])
    assert ta.nearest_levels(swing_highs, swing_lows, 50, 112.0) == (105.0, 120.0)
    assert ta.market_structure(swing_highs, swing_lows, 50) == 1


def test_rsi_bullish_divergence():
    swing_lows = ta.Swings([(10, 100.0, 13), (20, 98.0, 23)])
    rsi = [50.0] * 30
    rsi[10], rsi[20] = 25.0, 35.0
    assert ta.rsi_divergence(ta.Swings([]), swing_lows, rsi, 25) == 1
    assert ta.rsi_divergence(ta.Swings([]), swing_lows, rsi, 40) == 0    # خیلی قدیمی


@pytest.mark.parametrize("candles, expected", [
    ([(10, 10.5, 9.5, 10), (10.2, 10.3, 9.6, 9.7), (9.6, 10.5, 9.5, 10.4)], "پوشای صعودی"),
    ([(10, 10.5, 9.5, 10), (9.7, 10.3, 9.6, 10.2), (10.3, 10.4, 9.5, 9.6)], "پوشای نزولی"),
    ([(10, 10.5, 9.5, 10), (10, 10.1, 9.9, 10), (10, 10.05, 9.0, 10.02)], "چکش / پین‌بار صعودی"),
])
def test_candle_patterns(candles, expected):
    opens, highs, lows, closes = (list(x) for x in zip(*candles))
    assert ta.candle_pattern(opens, highs, lows, closes, 2)[1] == expected


# ---------------------------------------------------------------- خروج

def test_breakeven_price_covers_both_fees():
    price = exits.breakeven_price("LONG", 100.0, 0.0006)
    pnl = (price * (1 - 0.0006)) - 100.0 * (1 + 0.0006)
    assert pnl == pytest.approx(0.0, abs=1e-9)
    assert exits.breakeven_price("SHORT", 100.0, 0.0006) < 100.0


def _run(highs, lows, be=1.0):
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    return exits.simulate_exit("LONG", 100.0, 98.0, 104.0, highs, lows, closes, 0, len(highs), 0.0006, be)


def test_exit_moves_stop_after_one_r_and_closes_at_breakeven():
    r = _run([102.5, 101.0], [100.5, 99.0])
    assert r["result"] == "BREAKEVEN" and r["moved_to_breakeven"]
    assert r["exit_price"] == pytest.approx(exits.breakeven_price("LONG", 100.0, 0.0006))


def test_exit_without_breakeven_is_a_full_loss():
    assert _run([102.5, 101.0], [100.5, 97.0], be=None)["result"] == "LOSS"


def test_breakeven_takes_effect_only_from_the_next_candle():
    # همان کندلی که +1R را لمس کرده، به زیر نقطه‌ی ورود هم رفته: هنوز حد ضرر اولیه معتبر است
    r = _run([102.5, 101.0], [99.0, 100.5])
    assert r["result"] == "OPEN" and r["moved_to_breakeven"]


def test_exit_win_and_stop_first_when_both_touched():
    assert _run([104.5], [100.0])["result"] == "WIN"
    assert _run([104.5], [97.0])["result"] == "LOSS"


def test_backtest_records_breakeven_trades():
    from src.futures import backtest
    from test_signals import _candles_after_signal
    candles = _candles_after_signal("up", [(1.001, 0.999)] + [(1.06, 1.0)] + [(1.0, 0.9)], shape="dip")
    plain = backtest.backtest_symbol("T", candles, "dip")[-1]
    be = backtest.backtest_symbol("T", candles, "dip", breakeven_at_r=1.0)[-1]
    assert plain["result"] in ("LOSS", "WIN")
    if plain["result"] == "LOSS":
        assert be["result"] == "BREAKEVEN" and abs(be["r"]) < 0.05
    s = backtest.summarize([be, {"result": "WIN", "r": 2.0, "closed": "9"}])
    assert s["breakevens"] == (1 if be["result"] == "BREAKEVEN" else 0)


# ---------------------------------------------------------------- هم‌گرایی

_W = [0.8, 0.6, 0.7, -0.3, 0.75, 0.65, -0.25, 0.7, 0.6, -0.2]


def confluence_candles(n=400):
    """روند صعودی، رالی، اصلاح تا حمایت، و در آخر یک کندل پوشای صعودی با حجم بالا."""
    price, out, t0 = 100.0, [], 1791417600000
    changes = [_W[i % 10] * 0.4 for i in range(n - 40)]
    seg = [0.6] * 12 + [-0.5] * 14 + [0.1, -0.15]
    changes += seg + [-0.35] * (40 - len(seg) - 2)
    for i, ch in enumerate(changes):
        o = price
        c = price * (1 + ch / 100)
        w = abs(c - o) * 0.3 + price * 0.0008
        out.append([t0 + i * 3600000, o, max(o, c) + w, min(o, c) - w, c, 100.0])
        price = c
    po, pc = out[-1][1], out[-1][4]
    o, c = pc * 0.999, po * 1.004
    out.append([t0 + len(changes) * 3600000, o, c * 1.0008, o * 0.985, c, 220.0])
    return out


def test_confluence_long_on_textbook_setup():
    candles = confluence_candles()
    data = strategy.compute_indicators(candles)
    signal = strategy.confluence_signal_at(data, len(candles) - 1)
    assert signal is not None and signal["direction"] == "LONG"
    assert signal["stop"] < signal["entry"]
    assert "پوشای صعودی" in signal["reasons"]
    assert len(signal["reasons"]) >= 3          # الگو + مکان + دست‌کم ۲ تأیید (حداقل)


def test_confluence_is_silent_without_a_pattern_and_without_lookahead():
    candles = confluence_candles()
    data = strategy.compute_indicators(candles)
    assert strategy.confluence_signal_at(data, len(candles) - 2) is None
    # همان اندیس با کندل‌های بیشتر بعدش باید همان نتیجه را بدهد
    extra = candles + [[candles[-1][0] + 3600000 * k, 1, 1, 1, 1, 1] for k in range(1, 6)]
    a = strategy.confluence_signal_at(strategy.compute_indicators(candles), len(candles) - 1)
    b = strategy.confluence_signal_at(strategy.compute_indicators(extra), len(candles) - 1)
    assert a == b


def test_confluence_respects_crowded_funding():
    candles = confluence_candles()
    data = strategy.compute_indicators(candles)
    assert strategy.confluence_signal_at(data, len(candles) - 1, funding_percent=0.2) is None


# ---------------------------------------------------------------- پیگیری سیگنال زنده با سر‌به‌سر

def test_tracker_moves_stop_then_closes_at_breakeven(monkeypatch):
    from src.futures import signal_tracker as tracker
    opened = datetime.now() - timedelta(hours=3)
    record = {
        "id": 1, "symbol": "XUSDTM", "direction": "LONG", "score": 50, "entry_price": 100.0,
        "stop_loss_price": 98.0, "initial_stop_price": 98.0, "take_profit_price": 104.0,
        "leverage": 3, "status": "OPEN", "opened_at": str(opened), "closed_at": None, "closed_price": None,
    }
    saved = []
    monkeypatch.setattr(tracker, "load_history", lambda: [dict(record)])
    monkeypatch.setattr(tracker, "save_history", lambda rows: saved.extend(rows))
    t = int(opened.timestamp() * 1000)

    # ۱) قیمت به +۱R رسید ولی برنگشته: فقط حد ضرر جابه‌جا می‌شود
    candles = [[t + 3600000, 100, 102.5, 100.2, 102, 1], [t + 7200000, 102, 102.4, 101.5, 102, 1]]
    tracker.update_open_signals(lambda s: {}, candle_fetcher=lambda s, f: candles, breakeven_at_r=1.0)
    assert saved[-1]["status"] == "OPEN"
    moved_stop = saved[-1]["stop_loss_price"]
    assert moved_stop == pytest.approx(exits.breakeven_price("LONG", 100.0, 0.0006))

    # ۲) اسکن بعدی: قیمت برگشت. چون از حد ضرر اولیه دوباره شبیه‌سازی می‌شود، نتیجه BREAKEVEN است
    record["stop_loss_price"] = moved_stop
    candles.append([t + 10800000, 102, 102, 99.5, 99.8, 1])
    tracker.update_open_signals(lambda s: {}, candle_fetcher=lambda s, f: candles, breakeven_at_r=1.0)
    assert saved[-1]["status"] == "BREAKEVEN"


def test_tracker_counts_breakevens_in_stats():
    from src.futures.signal_tracker import get_stats
    stats = get_stats([{"status": s} for s in ("WIN", "LOSS", "BREAKEVEN", "OPEN")])
    assert stats["breakevens"] == 1 and stats["closed"] == 3


# ---------------------------------------------------------------- اخبار

def test_sentiment_and_coin_detection():
    from src.news.sentiment import mentioned_coins, sentiment_score
    assert sentiment_score("Exchange hacked, $40M drained") <= -5
    assert sentiment_score("KuCoin will delist XYZ") == -3          # delist، نه list
    assert sentiment_score("SEC approves spot ETF, inflows surge") > 0
    assert mentioned_coins("Solana and $PEPE rally while the SEC and CEO talk") == {"SOL", "PEPE"}
    assert mentioned_coins("XBT hits new high") == {"BTC"}


def test_parse_rss_and_atom():
    from src.news.feeds import parse_feed
    rss = parse_feed(b"""<rss><channel><item><title>A <b>bold</b> title</title><link>https://x/a</link>
        <pubDate>Wed, 21 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>""", "S")
    assert "bold" in rss[0]["title"] and "<b>" not in rss[0]["title"]
    assert rss[0]["link"] == "https://x/a" and rss[0]["published"].year == 2026
    atom = parse_feed(b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title>
        <link href="https://x/b"/><updated>2026-10-21T10:00:00Z</updated></entry></feed>""", "S")
    assert atom[0]["link"] == "https://x/b" and atom[0]["published"].hour == 10


def _opp(symbol="SOLUSDTM", direction="LONG", confidence=60):
    return {"symbol": symbol, "direction": direction, "confidence": confidence, "score": confidence}


def test_apply_news_blocks_delisted_macro_and_bad_news():
    from src.futures.scanner import apply_news
    from src.news.feeds import empty_news_context
    news = empty_news_context()
    news["delisted_coins"] = {"XYZ"}
    news["coin_scores"] = {"SOL": -4, "ETH": 2}
    assert apply_news(_opp("XYZUSDTM"), news, None)["blocked_reason"]
    assert apply_news(_opp("SOLUSDTM"), news, None)["blocked_reason"]          # خبر بد برای Long
    assert apply_news(_opp("SOLUSDTM", "SHORT"), news, None)["blocked_reason"] is None
    eth = apply_news(_opp("ETHUSDTM", confidence=60), news, None)
    assert eth["blocked_reason"] is None and eth["confidence"] == 66
    event = {"title": "CPI m/m", "time": datetime.now(timezone.utc)}
    assert "CPI" in apply_news(_opp("ETHUSDTM"), news, event)["blocked_reason"]


def test_macro_risk_window():
    from src.news.feeds import macro_risk_now
    now = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
    ctx = {"macro_events": [{"title": "FOMC", "time": now + timedelta(minutes=90)}]}
    assert macro_risk_now(ctx, now=now)["title"] == "FOMC"
    assert macro_risk_now(ctx, now=now - timedelta(hours=3)) is None


def test_build_news_context_with_fake_sources(monkeypatch):
    from unittest import mock
    from fake_kucoin import fake_get
    import fake_kucoin
    from src.news import feeds
    monkeypatch.setattr(fake_kucoin, "DELISTINGS", [
        {"annTitle": "KuCoin Will Delist FOO (FOO)", "annUrl": "https://k/1",
         "cTime": int(datetime.now().timestamp() * 1000)}])
    with mock.patch("requests.get", side_effect=fake_get):
        ctx = feeds.build_news_context(force=True)
    assert ctx["errors"] == []
    assert ctx["coin_scores"]["BTC"] > 0
    assert "FOO" in ctx["delisted_coins"]
    assert ctx["trending"][0]["symbol"] == "PEPE"


# ---------------------------------------------------------------- خروج پله‌ای

def test_trade_plan_with_scale_out_keeps_one_to_two_on_average():
    from src.futures.futures_risk import build_trade_plan, net_reward_risk
    plan = build_trade_plan("LONG", 100.0, 98.0, 1000, 1, 5, min_reward_risk=3.0,
                            scale_out={"tp1_r": 1.0, "fraction": 0.5})
    tp1, tp2 = plan["take_profit_1_price"], plan["take_profit_price"]
    assert 100 < tp1 < tp2
    assert net_reward_risk("LONG", 100.0, 98.0, tp1, 0.0006) == pytest.approx(1.0, abs=0.01)
    assert net_reward_risk("LONG", 100.0, 98.0, tp2, 0.0006) == pytest.approx(3.0, abs=0.01)
    assert plan["reward_risk_ratio"] == pytest.approx(2.0, abs=0.02)
    assert build_trade_plan("SHORT", 100.0, 102.0, 1000, 1, 5)["take_profit_1_price"] is None


def _tps():
    from src.futures.futures_risk import target_for_r
    return target_for_r("LONG", 100.0, 98.0, 1.0, 0.0006), target_for_r("LONG", 100.0, 98.0, 3.0, 0.0006)


def _scaled(highs, lows):
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    tp1, tp2 = _tps()
    return exits.simulate_scaled_exit("LONG", 100.0, 98.0, tp1, tp2, highs, lows, closes,
                                      0, len(highs), 0.0006)


@pytest.mark.parametrize("highs, lows, result, r", [
    ([101.0, 100.5], [99.0, 97.5], "LOSS", -1.0),            # حد ضرر قبل از پله‌ی اول
    ([102.5, 101.0], [100.5, 99.5], "PARTIAL", 0.5),          # پله‌ی اول، بعد سر‌به‌سر
    ([102.5, 107.0], [100.5, 101.0], "WIN", 2.0),             # هر دو پله
    ([107.0], [100.5], "WIN", 2.0),                           # هر دو در یک کندل
    ([102.5], [97.0], "LOSS", -1.0),                          # همان کندل هر دو: بدبینانه ضرر
])
def test_scaled_exit_outcomes(highs, lows, result, r):
    out = _scaled(highs, lows)
    assert out["result"] == result
    got = exits.scaled_r("LONG", 100.0, 98.0, _tps()[0], 0.5, out["exit_price"],
                         out["tp1_index"] is not None, 0.0006)
    assert got == pytest.approx(r, abs=0.03)


def test_backtest_scale_out_labels_partial_and_counts_profit_rate():
    from src.futures import backtest
    from test_signals import _candles_after_signal
    # بعد از سیگنال: کمی بالا (پله‌ی اول)، بعد برگشت شدید
    candles = _candles_after_signal("up", [(1.001, 0.999), (1.06, 1.0), (1.0, 0.8)], shape="dip")
    trade = backtest.backtest_symbol("T", candles, "dip", min_reward_risk=3.0,
                                     scale_out={"tp1_r": 1.0, "fraction": 0.5})[-1]
    assert trade["result"] in ("PARTIAL", "WIN")
    assert trade["r"] > 0
    s = backtest.summarize([trade, {"result": "LOSS", "r": -1.0, "closed": "z"}])
    assert s["profit_rate"] == 50.0 and s["partials"] + s["wins"] == 1


def test_tracker_scale_out_partial_and_pnl(monkeypatch):
    from src.futures import signal_tracker as tracker
    opened = datetime.now() - timedelta(hours=3)
    record = {
        "id": 7, "symbol": "XUSDTM", "direction": "LONG", "score": 50, "entry_price": 100.0,
        "stop_loss_price": 98.0, "initial_stop_price": 98.0, "take_profit_price": 106.3,
        "take_profit_1_price": 102.1, "partial_fraction": 0.5,
        "leverage": 3, "status": "OPEN", "opened_at": str(opened), "closed_at": None, "closed_price": None,
    }
    saved = []
    monkeypatch.setattr(tracker, "load_history", lambda: [dict(record)])
    monkeypatch.setattr(tracker, "save_history", lambda rows: saved.extend(rows))
    t = int(opened.timestamp() * 1000)
    candles = [[t + 3600000, 100, 102.5, 100.2, 102, 1], [t + 7200000, 102, 102.2, 99.0, 99.5, 1]]
    tracker.update_open_signals(lambda s: {}, candle_fetcher=lambda s, f: candles, breakeven_at_r=1.0)
    closed = saved[-1]
    assert closed["status"] == "PARTIAL"
    # نصف در +۲٫۱٪ و نصف در سر‌به‌سر (حدود +۰٫۱۲٪)
    assert tracker.calculate_pnl_percent(closed) == pytest.approx(1.11, abs=0.03)
    stats = tracker.get_stats([closed, {"status": "LOSS"}])
    assert stats["partials"] == 1 and stats["profit_rate"] == 50.0 and stats["win_rate"] == 0


def test_scanner_uses_scale_out_setting(monkeypatch):
    import config.settings as settings
    from unittest import mock
    from fake_kucoin import fake_get
    from src.futures.scanner import scan_market
    from src.news.feeds import empty_news_context
    monkeypatch.setattr(settings, "SCALE_OUT", {"tp1_r": 1.0, "fraction": 0.5})
    with mock.patch("requests.get", side_effect=fake_get):
        result = scan_market(top_n=6, capital=200, news_fetcher=empty_news_context)
    opportunities = result["longs"] + result["shorts"]
    assert opportunities, "the fake market should produce at least one signal"
    for o in opportunities:
        assert o["take_profit_1_price"] is not None and o["reward_risk_ratio"] >= 1.98
