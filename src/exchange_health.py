"""
تست سریع اتصال به هر منبع داده‌ی کوکوین که پنل استفاده می‌کند.

هدف: اگر روی یک هاست جدید چیزی کار نکرد، از داخل خود پنل معلوم شود کدام
بخش (اسپات، فیوچرز، Open Interest) جواب نمی‌دهد و چرا، بدون نیاز به ترمینال.
"""

from src.candle_data import get_spot_candles
from src.futures.fundamental_engine import get_funding_rate, get_open_interest_trend
from src.futures.futures_market_data import get_active_contracts, get_futures_klines
from src.market_data import get_spot_price


def check_kucoin_connectivity():

    checks = [
        ("قیمت اسپات BTC-USDT", lambda: "$" + format(get_spot_price("BTC-USDT"), ",.2f")),
        ("کندل‌های اسپات", lambda: str(len(get_spot_candles("BTC-USDT", "1h", 5))) + " کندل"),
        ("لیست قراردادهای فیوچرز", lambda: str(len(get_active_contracts(max_age_seconds=0))) + " قرارداد"),
        ("کندل‌های فیوچرز XBTUSDTM", lambda: str(len(get_futures_klines("XBTUSDTM", "1h", 5))) + " کندل"),
        ("نرخ فاندینگ XBTUSDTM", lambda: format(get_funding_rate("XBTUSDTM"), ".4f") + "٪"),
        ("روند Open Interest XBTUSDTM", lambda: format(get_open_interest_trend("XBTUSDTM"), "+.2f") + "٪"),
    ]

    results = []

    for name, check in checks:

        try:
            results.append({"بخش": name, "وضعیت": "✅", "جزئیات": check()})
        except Exception as error:
            results.append({"بخش": name, "وضعیت": "❌", "جزئیات": str(error)[:200]})

    return results
