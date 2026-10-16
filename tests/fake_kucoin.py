"""
A fake KuCoin for tests: routes requests.get(url, params, timeout) to fixtures
built from responses captured live from the KuCoin public API on 2026-10-16.
"""

import time
from unittest import mock

CALLS = []

# --- spot level1, verbatim shape from api.kucoin.com ---
SPOT_PRICES = {"BTC-USDT": "82114", "ETH-USDT": "2451.36", "LINK-USDT": "12.6634",
               "ONDO-USDT": "0.47388", "NEAR-USDT": "5.2823"}


def spot_candles_newest_first(n=100):
    # first two rows are the real live rows; older rows continue a gentle uptrend
    rows = [["1792141200", "82264", "82114.1", "82269.4", "82114", "52.06405916", "4280044.03"],
            ["1792137600", "82275.4", "82264.1", "82376.2", "82173.5", "90.9240692", "7480894.96"]]
    t, close = 1792137600, 82275.4
    for i in range(n - 2):
        t -= 3600
        open_ = close - (60 if i % 3 else -40)
        high, low = max(open_, close) + 25, min(open_, close) - 25
        rows.append([str(t), str(open_), str(close), str(high), str(low), "10", "1"])
        close = open_
    return rows


# --- futures contracts: real fields; plus the traps the filter must reject ---
def contract(symbol, base, turnover, last, funding, **extra):
    c = {"symbol": symbol, "baseCurrency": base, "quoteCurrency": "USDT", "settleCurrency": "USDT",
         "type": "FFWCSX", "expireDate": None, "isInverse": False, "status": "Open",
         "multiplier": 0.001, "turnoverOf24h": turnover, "volumeOf24h": 1.0,
         "lastTradePrice": last, "markPrice": last, "fundingFeeRate": funding,
         "openInterest": "1000", "marketType": "CRYPTO", "assetClass": "CRYPTO", "marketStage": "NORMAL"}
    c.update(extra)
    return c


CONTRACTS = [
    contract("XBTUSDTM", "XBT", 3.825995576152E8, 82072.9, 1.0E-4),
    contract("ETHUSDTM", "ETH", 2.470498704498E8, 2449.71, 8.3E-5),
    contract("SOLUSDTM", "SOL", 6.60677789708E7, 106.374, 8.8E-5),
    contract("PEPEUSDTM", "PEPE", 4.0666153347248E7, 4.0879E-6, 1.0E-4),
    contract("DOGEUSDTM", "DOGE", 2.5394813792E7, 0.08228, 1.0E-4),
    contract("XRPUSDTM", "XRP", 3.23762307944E7, 1.33852, 1.0E-4),
    # traps: must never be scanned even though some have huge turnover
    contract("AAPLUSDTM", "AAPL", 9.9E9, 342.47, 0.0, marketType="NASDAQ", assetClass="STOCK"),
    contract("XBTUSDM", "XBT", 9.8E9, 82070.0, 1.0E-4, quoteCurrency="USD", isInverse=True),
    contract("NEWUSDTM", "NEW", 9.7E9, 1.0, 1.0E-4, marketStage="PRE_MARKET"),
    contract("XBTMZ26", "XBT", 9.6E9, 82500.0, 0.0, expireDate=1798761600000),
    contract("HALTUSDTM", "HALT", 9.5E9, 1.0, 0.0, status="Paused"),
]


def futures_klines_oldest_first(symbol, n=500):
    # the live strategy's textbook setups, ending with the last *closed* hour:
    # "up" symbols give a Long, the others the mirror image (a Short).
    from src.futures.demo_data import synthetic_candles
    now_ms = int(time.time() * 1000)
    end_ms = now_ms // 3_600_000 * 3_600_000            # the last candle has just closed
    start_ms = end_ms - n * 3_600_000
    up = symbol in ("XBTUSDTM", "SOLUSDTM", "XRPUSDTM")
    from config.settings import SIGNAL_STRATEGY
    rows = synthetic_candles("up" if up else "down", n, 100.0, start_ms, shape=SIGNAL_STRATEGY)
    last = float(next(c for c in CONTRACTS if c["symbol"] == symbol)["lastTradePrice"])
    scale = last / rows[-1][4]
    return [[c[0]] + [v * scale for v in c[1:5]] + [c[5], 1] for c in rows]


# real OI history for XBTUSDTM (newest first)
OI_HISTORY = [{"openInterest": "9361133", "ts": 1792141200000}, {"openInterest": "9259824", "ts": 1792137600000},
              {"openInterest": "9242477", "ts": 1792134000000}, {"openInterest": "9203760", "ts": 1792130400000},
              {"openInterest": "9196234", "ts": 1792126800000}, {"openInterest": "9184714", "ts": 1792123200000},
              {"openInterest": "9351399", "ts": 1792119600000}]


def _resp(status, payload):
    r = mock.Mock()
    r.status_code = status
    r.json.return_value = payload
    return r


def fake_get(url, params=None, timeout=None):
    CALLS.append((url, dict(params or {}), timeout))
    params = params or {}
    ok = lambda data: _resp(200, {"code": "200000", "data": data})
    if url == "https://api.kucoin.com/api/v1/market/orderbook/level1":
        price = SPOT_PRICES.get(params["symbol"])
        return ok({"time": 1792143674868, "price": price, "bestBid": price} if price else None)
    if url == "https://api.kucoin.com/api/v1/market/candles":
        return ok(spot_candles_newest_first())
    if url == "https://api-futures.kucoin.com/api/v1/contracts/active":
        return ok(CONTRACTS)
    if url == "https://api-futures.kucoin.com/api/v1/kline/query":
        # like the real API: only candles inside [from, to], and at most 200 of them
        rows = [r for r in futures_klines_oldest_first(params["symbol"])
                if params["from"] <= r[0] <= params["to"]]
        return ok(rows[-200:])
    if url == "https://api-futures.kucoin.com/api/v1/contract/funding-rates":
        return ok([{"symbol": params["symbol"], "fundingRate": 0.0001, "timepoint": params["from"] + 8 * 3_600_000}])
    if url == "https://api.kucoin.com/api/ua/v1/market/open-interest":
        return ok(OI_HISTORY[: int(params.get("pageSize", 7))])
    if "alternative.me" in url:
        return _resp(200, {"data": [{"value": "55"}]})
    raise AssertionError("unexpected URL in test: " + url)
