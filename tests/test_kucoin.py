"""
تست‌های لایه‌ی داده‌ی کوکوین و خود پنل، بدون اتصال واقعی به اینترنت.

داده‌های تست (tests/fake_kucoin.py) از پاسخ‌های زنده‌ی API عمومی کوکوین
ساخته شده‌اند. اجرا از ریشه‌ی پروژه:

    pip install -r requirements-dev.txt
    pytest
"""

import os
from unittest import mock

import pytest
import requests

import fake_kucoin
from fake_kucoin import fake_get


@pytest.fixture(autouse=True)
def kucoin():
    fake_kucoin.CALLS.clear()
    import src.futures.futures_market_data as fmd
    fmd._contracts_cache.update(at=0.0, by_symbol={})
    with mock.patch("requests.get", side_effect=fake_get):
        yield fake_kucoin.CALLS


# ---------------- spot ----------------

def test_spot_price_and_portfolio_prices():
    from config.settings import ASSET_SYMBOLS
    from src.market_data import get_prices, get_spot_price
    assert get_spot_price("BTC-USDT") == 82114.0
    prices = get_prices(ASSET_SYMBOLS)
    assert prices == {"BTC": 82114.0, "ETH": 2451.36, "LINK": 12.6634, "ONDO": 0.47388, "NEAR": 5.2823}


def test_unknown_spot_symbol_is_a_clear_error_not_zero():
    from src.exchange_client import ExchangeUnavailable
    from src.market_data import get_spot_price
    with pytest.raises(ExchangeUnavailable, match="NOTREAL-USDT"):
        get_spot_price("NOTREAL-USDT")


def test_spot_candles_are_reordered_to_the_old_shape(kucoin):
    from src.candle_data import get_spot_candles
    candles = get_spot_candles("BTC-USDT", "1h", 100)
    assert len(candles) == 100
    times = [c[0] for c in candles]
    assert times == sorted(times), "must be oldest -> newest"
    newest = candles[-1]
    # real live row: ["1792141200","82264","82114.1","82269.4","82114",...] = [t, o, c, h, l]
    assert newest == [1792141200000, 82264.0, 82269.4, 82114.0, 82114.1, 52.06405916]
    assert newest[4] == 82114.1, "close must be at index 4 like Binance"
    for c in candles:
        assert c[2] >= max(c[1], c[4]) and c[3] <= min(c[1], c[4]), "high/low must bound open/close"
    url, params, timeout = kucoin[-1]
    assert params["type"] == "1hour" and params["symbol"] == "BTC-USDT" and timeout == 15
    assert params["endAt"] - params["startAt"] == 101 * 3600 and params["endAt"] < 10**11, "seconds, not ms"


def test_btc_candles_feed_the_old_analysis():
    from src.analysis.analysis_loader import AnalysisLoader
    from src.candle_data import get_btc_candles
    result = AnalysisLoader().analyze(get_btc_candles(), 82114.0)
    assert result["ma"] and 0 <= result["rsi"] <= 100


# ---------------- futures ----------------

def test_top_symbols_exclude_stocks_inverse_premarket_expiring_and_paused():
    from src.futures.futures_market_data import get_top_symbols_by_volume
    top = get_top_symbols_by_volume(10)
    assert top == ["XBTUSDTM", "ETHUSDTM", "SOLUSDTM", "PEPEUSDTM", "XRPUSDTM", "DOGEUSDTM"]
    for trap in ("AAPLUSDTM", "XBTUSDM", "NEWUSDTM", "XBTMZ26", "HALTUSDTM"):
        assert trap not in top


def test_futures_klines_normalized(kucoin):
    from src.futures.futures_market_data import get_futures_klines
    candles = get_futures_klines("XBTUSDTM", "1h", 100)
    assert len(candles) == 100
    assert [c[0] for c in candles] == sorted(c[0] for c in candles)
    assert all(len(c) == 6 for c in candles)
    url, params, _ = kucoin[-1]
    assert params["granularity"] == 60
    assert params["to"] - params["from"] == 101 * 3_600_000 and params["to"] > 10**12, "milliseconds"


def test_funding_uses_one_contract_request_for_a_whole_scan(kucoin):
    from src.futures.fundamental_engine import get_funding_rate
    from src.futures.futures_market_data import get_top_symbols_by_volume
    symbols = get_top_symbols_by_volume(6)
    rates = {s: get_funding_rate(s) for s in symbols}
    assert rates["XBTUSDTM"] == pytest.approx(0.01)       # 1.0E-4 -> 0.01 %
    assert rates["ETHUSDTM"] == pytest.approx(0.0083)
    contract_calls = [c for c in kucoin if c[0].endswith("/contracts/active")]
    assert len(contract_calls) == 1


def test_open_interest_trend_from_real_history(kucoin):
    from src.futures.fundamental_engine import get_open_interest_trend
    trend = get_open_interest_trend("XBTUSDTM", lookback=7)
    # oldest 9351399 -> newest 9361133
    assert trend == pytest.approx((9361133 - 9351399) / 9351399 * 100)
    url, params, _ = kucoin[-1]
    assert url == "https://api.kucoin.com/api/ua/v1/market/open-interest"
    assert params == {"symbol": "XBTUSDTM", "interval": "1hour", "pageSize": 7}


def test_futures_prices_skip_unknown_old_binance_symbols():
    from src.futures.futures_market_data import get_futures_prices
    assert get_futures_prices(["XBTUSDTM", "BTCUSDT"]) == {"XBTUSDTM": 82072.9}


def test_full_scan_end_to_end():
    from src.futures.scanner import scan_market
    result = scan_market(top_n=6, capital=200)
    assert result["scanned"] == 6 and not result["skipped"], result["skipped"]
    longs = {o["symbol"] for o in result["longs"]}
    shorts = {o["symbol"] for o in result["shorts"]}
    assert longs == {"XBTUSDTM", "SOLUSDTM", "XRPUSDTM"}, (longs, shorts)
    assert shorts == {"ETHUSDTM", "PEPEUSDTM", "DOGEUSDTM"}, (longs, shorts)
    for o in result["longs"]:
        assert o["stop_loss_price"] < o["entry_price"] < o["take_profit_price"], o
    for o in result["shorts"]:
        assert o["take_profit_price"] < o["entry_price"] < o["stop_loss_price"], o


# ---------------- error handling ----------------

def _one(status, payload=None, exc=None):
    r = mock.Mock(status_code=status)
    r.json.return_value = payload
    return mock.patch("requests.get", side_effect=exc) if exc else mock.patch("requests.get", return_value=r)


def test_geo_block_is_explained():
    from src.exchange_client import ExchangeUnavailable, kucoin_get
    with _one(451, {"msg": "restricted"}), pytest.raises(ExchangeUnavailable, match="محدودیت منطقه‌ای"):
        kucoin_get("https://api.kucoin.com/api/v1/market/orderbook/level1")


def test_kucoin_error_code_is_surfaced():
    from src.exchange_client import ExchangeUnavailable, kucoin_get
    with _one(200, {"code": "400100", "msg": "Unsupported trading pair."}), \
         pytest.raises(ExchangeUnavailable, match="400100.*Unsupported trading pair"):
        kucoin_get("https://api.kucoin.com/api/v1/market/orderbook/level1")


def test_timeout_is_explained():
    from src.exchange_client import ExchangeUnavailable, kucoin_get
    with _one(0, exc=requests.Timeout("slow")), pytest.raises(ExchangeUnavailable, match="Timeout"):
        kucoin_get("https://api-futures.kucoin.com/api/v1/contracts/active")


# ---------------- the panel itself ----------------

def _app(page):
    from src.password_utils import hash_password
    from streamlit.testing.v1 import AppTest
    os.environ["APP_PASSWORD_SALT"] = "s"
    os.environ["APP_PASSWORD_HASH"] = hash_password("p", "s")
    at = AppTest.from_file(page)
    at.session_state["authenticated"] = True
    return at


def test_dashboard_scan_and_health_check_render():
    at = _app("dashboard.py")
    at.run(timeout=60)
    assert not at.exception
    by_label = {b.label: b for b in at.button}
    by_label["🩺 تست اتصال به کوکوین"].click().run(timeout=60)
    assert not at.exception
    assert any("همه‌ی منابع داده‌ی کوکوین" in s.value for s in at.success), [e.value for e in at.error]
    by_label = {b.label: b for b in at.button}
    by_label["🔄 اسکن بازار"].click().run(timeout=60)
    assert not at.exception
    assert not at.error, [e.value for e in at.error]
    assert any("تعداد ارزهای بررسی‌شده" in m.value for m in at.markdown)


def test_dca_page_renders_with_kucoin_prices():
    at = _app("pages/1_Spot_DCA_Portfolio.py")
    at.run(timeout=60)
    assert not at.exception
    price_warnings = [w.value for w in at.warning if "کوکوین" in w.value]
    assert not price_warnings, price_warnings


def test_storage_status_warns_while_data_is_only_in_sqlite():
    at = _app("dashboard.py")
    at.run(timeout=60)
    assert any("SQLite" in w.value and "DATABASE_URL" in w.value for w in at.sidebar.warning)


def test_storage_status_is_calm_on_postgres():
    import src.ui_common as ui
    fake_engine = mock.Mock()
    fake_engine.dialect.name = "postgresql"
    with mock.patch.object(ui, "engine", fake_engine):
        at = _app("dashboard.py")
        at.run(timeout=60)
    assert not any("SQLite" in w.value for w in at.sidebar.warning)
    assert any("Postgres" in c.value for c in at.sidebar.caption)
