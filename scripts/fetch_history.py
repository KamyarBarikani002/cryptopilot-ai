"""
تاریخچه‌ی بازار فیوچرز کوکوین را برای بک‌تست دانلود می‌کند.

خروجی (پوشه‌ی history/):
- klines_1h.csv.gz : symbol,time_ms,open,high,low,close,volume
- funding.csv.gz   : symbol,time_ms,funding_rate (کسری، مثل 0.0001)
- fear_greed.csv   : time_s,value
- contracts.json   : tickSize و ... قراردادهای انتخاب‌شده

اجرا:  python3 scripts/fetch_history.py --top 30 --days 180
(روی سیستمی که به api-futures.kucoin.com دسترسی دارد)
"""

import argparse
import csv
import gzip
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.futures.fundamental_engine import get_funding_history  # noqa: E402
from src.futures.futures_market_data import (  # noqa: E402
    get_active_contracts,
    get_futures_klines_range,
    get_top_symbols_by_volume,
)

HOUR_MS = 3_600_000


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--out", default="history")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    end_ms = int(time.time() // 3600 * 3600 * 1000)
    start_ms = end_ms - args.days * 24 * HOUR_MS

    symbols = get_top_symbols_by_volume(args.top)
    contracts = get_active_contracts()
    print("symbols:", symbols)

    with open(os.path.join(args.out, "contracts.json"), "w") as f:
        json.dump({
            s: {k: contracts[s].get(k) for k in (
                "tickSize", "lotSize", "multiplier", "takerFeeRate", "makerFeeRate",
                "maxLeverage", "turnoverOf24h", "lastTradePrice")}
            for s in symbols
        }, f, indent=1)

    with gzip.open(os.path.join(args.out, "klines_1h.csv.gz"), "wt", newline="") as kf, \
            gzip.open(os.path.join(args.out, "funding.csv.gz"), "wt", newline="") as ff:

        kw, fw = csv.writer(kf), csv.writer(ff)
        kw.writerow(["symbol", "time_ms", "open", "high", "low", "close", "volume"])
        fw.writerow(["symbol", "time_ms", "funding_rate"])

        for symbol in symbols:

            candles = get_futures_klines_range(symbol, "1h", start_ms, end_ms)
            for candle in candles:
                kw.writerow([symbol] + [repr(v) for v in candle])

            try:
                funding = get_funding_history(symbol, start_ms, end_ms)
            except Exception as error:  # تاریخچه‌ی فاندینگ اختیاری است
                print("  funding", symbol, "failed:", error)
                funding = []
            for t, percent in funding:
                fw.writerow([symbol, t, repr(percent / 100)])

            print(symbol, "candles:", len(candles), "funding:", len(funding))

    response = requests.get("https://api.alternative.me/fng/", params={"limit": args.days + 5}, timeout=20)
    with open(os.path.join(args.out, "fear_greed.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "value"])
        for item in response.json()["data"]:
            w.writerow([item["timestamp"], item["value"]])

    print("done")


if __name__ == "__main__":
    main()
