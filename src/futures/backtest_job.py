"""
اجرای بک‌تست در پس‌زمینه.

دانلود چند ماه کندل برای ۲۰ ارز چند دقیقه طول می‌کشد. اگر این کار داخل خود
اجرای صفحه باشد، با هر قطع و وصل شدن اتصال مرورگر (که روی Streamlit Cloud پیش
می‌آید) نیمه‌کاره رها می‌شود. اینجا کار در یک thread جدا انجام می‌شود و
نتیجه‌ی آخرین اجرا در حافظه‌ی سرور می‌ماند؛ صفحه فقط وضعیت را نشان می‌دهد.
"""

import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from config.settings import FUTURES_TAKER_FEE_PERCENT, REWARD_RISK_RATIO
from src.futures.backtest import backtest_symbol

HOUR_MS = 3_600_000
WARMUP_CANDLES = 300

# اولین ردیف = استراتژی فعلی اسکنر. بقیه برای مقایسه‌اند.
STRATEGY_VARIANTS = [
    ("خرید افت در روند — استراتژی فعلی اسکنر", "dip", {}),
    ("خرید افت + ADX ≥ 20", "dip", {"adx_min": 20}),
    ("خرید افت، RSI 35/65 (سیگنال بیشتر)", "dip", {"rsi_low": 35, "rsi_high": 65}),
    ("خرید افت، RSI 35/65 + ADX ≥ 20", "dip", {"rsi_low": 35, "rsi_high": 65, "adx_min": 20}),
    ("پولبک در جهت روند (EMA + ADX)", "pullback", {}),
]


class BacktestJob:

    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"            # idle | running | done | error
        self.progress = 0.0
        self.message = ""
        self.report = None
        self.error = None
        self.thread = None
        self._history_cache = {}        # (symbol, start, end, funding) -> data

    def snapshot(self):
        with self.lock:
            return {
                "status": self.status, "progress": self.progress, "message": self.message,
                "report": self.report, "error": self.error,
            }

    def start(self, settings, fetchers):

        with self.lock:
            if self.status == "running":
                return False
            self.status, self.progress, self.message, self.error = "running", 0.0, "شروع...", None

        self.thread = threading.Thread(target=self._run, args=(settings, fetchers), daemon=True)
        self.thread.start()
        return True

    def _set(self, **values):
        with self.lock:
            for key, value in values.items():
                setattr(self, key, value)

    def _run(self, settings, fetchers):

        try:
            self._set(report=self._compute(settings, fetchers), status="done", progress=1.0, message="")
        except Exception as error:
            self._set(status="error", error=str(error) + "\n" + traceback.format_exc(limit=3))

    def _load(self, symbol, start_ms, end_ms, s, f):

        """
        تاریخچه‌ی یک ارز. برای اینکه ۴۰۰+ ارز در حافظه‌ی سرور جا شوند، کندل‌ها
        فشرده (numpy) نگه داشته می‌شوند و فقط موقع بک‌تست به لیست تبدیل می‌شوند.
        """

        key = (symbol, start_ms, end_ms, s["use_funding"])
        problems = []

        if key not in self._history_cache:
            candles = f["klines"](symbol, "1h", start_ms, end_ms)
            funding = []
            if s["use_funding"]:
                try:
                    funding = f["funding"](symbol, start_ms, end_ms)
                except Exception as error:
                    problems.append(symbol + " (فاندینگ): " + str(error))
            self._history_cache[key] = (np.asarray(candles, dtype=np.float64), funding, f["tick"](symbol))

        return self._history_cache[key], problems

    def _compute(self, s, f):

        started = time.time()
        end_ms = int(started // 3600 * 3600 * 1000)
        start_ms = end_ms - (s["days"] * 24 + WARMUP_CANDLES) * HOUR_MS

        symbols = f["symbols"](s["top_n"])
        failed, timings = [], {}
        results = {label: [] for label, _, _ in STRATEGY_VARIANTS}
        done = 0

        def work(symbol):
            t0 = time.time()
            (candles, funding, tick), problems = self._load(symbol, start_ms, end_ms, s, f)
            rows = [[int(c[0])] + list(c[1:]) for c in candles.tolist()]
            per_variant = {
                label: backtest_symbol(
                    symbol, rows, name, params,
                    funding_points=funding,
                    min_reward_risk=REWARD_RISK_RATIO, fee_percent=FUTURES_TAKER_FEE_PERCENT,
                    max_hold=s["max_hold"], tick_size=tick,
                )
                for label, name, params in STRATEGY_VARIANTS
            } if len(rows) else {}
            return per_variant, problems, round(time.time() - t0, 1)

        # چند ارز همزمان (کوکوین درخواست‌های عمومی را محدود می‌کند؛ ۶ تا امن است)
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(work, symbol): symbol for symbol in symbols}
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    per_variant, problems, seconds = future.result()
                    for label, trades in per_variant.items():
                        results[label] += trades
                    failed += problems
                    timings[symbol] = seconds
                except Exception as error:
                    failed.append(symbol + ": " + str(error))
                done += 1
                self._set(
                    progress=done / max(len(symbols), 1),
                    message=str(done) + " از " + str(len(symbols)) + " ارز — آخرین: " + symbol,
                )

        results = [(label, results[label]) for label, _, _ in STRATEGY_VARIANTS]
        loaded = [sym for sym in symbols if sym in timings]

        return {
            "results": results,
            "failed": failed,
            "symbols": loaded,
            "settings": dict(s),
            "seconds": round(time.time() - started),
            "timings": timings,
            "ran_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
            "middle": time.strftime("%Y-%m-%d %H:%M", time.gmtime((end_ms - s["days"] * 12 * HOUR_MS) / 1000)),
        }
