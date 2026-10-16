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

from config.settings import FUTURES_TAKER_FEE_PERCENT, REWARD_RISK_RATIO
from src.futures.backtest import backtest_symbol

HOUR_MS = 3_600_000
WARMUP_CANDLES = 300

STRATEGY_VARIANTS = [
    ("نسخه‌ی جدید (پولبک در جهت روند)", "v2", {}),
    ("نسخه‌ی جدید بدون فیلتر روند ۴ ساعته", "v2", {"use_4h_filter": False}),
    ("نسخه‌ی جدید بدون فیلتر ADX", "v2", {"use_adx_filter": False}),
    ("منطق قبلی (MA20 + RSI)", "v1", {}),
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

    def _compute(self, s, f):

        started = time.time()
        end_ms = int(started // 3600 * 3600 * 1000)
        start_ms = end_ms - (s["days"] * 24 + WARMUP_CANDLES) * HOUR_MS

        symbols = f["symbols"](s["top_n"])
        loaded, failed, timings = {}, [], {}

        for k, symbol in enumerate(symbols):

            self._set(progress=k / max(len(symbols), 1) * 0.9, message="دانلود " + symbol)
            t0 = time.time()
            key = (symbol, start_ms, end_ms, s["use_funding"])

            try:
                if key not in self._history_cache:
                    candles = f["klines"](symbol, "1h", start_ms, end_ms)
                    funding = []
                    if s["use_funding"]:
                        try:
                            funding = f["funding"](symbol, start_ms, end_ms)
                        except Exception as error:
                            failed.append(symbol + " (فاندینگ): " + str(error))
                    self._history_cache[key] = (candles, funding, f["tick"](symbol))
                loaded[symbol] = self._history_cache[key]
            except Exception as error:
                failed.append(symbol + ": " + str(error))

            timings[symbol] = round(time.time() - t0, 1)

        self._set(progress=0.92, message="اجرای بک‌تست...")

        results = []
        for label, name, params in STRATEGY_VARIANTS:
            trades = []
            for symbol, (candles, funding, tick) in loaded.items():
                trades += backtest_symbol(
                    symbol, candles, name, params,
                    funding_points=funding if name == "v2" else None,
                    min_reward_risk=REWARD_RISK_RATIO, fee_percent=FUTURES_TAKER_FEE_PERCENT,
                    max_hold=s["max_hold"], tick_size=tick,
                )
            results.append((label, trades))

        return {
            "results": results,
            "failed": failed,
            "symbols": list(loaded),
            "settings": dict(s),
            "seconds": round(time.time() - started),
            "timings": timings,
            "ran_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        }
