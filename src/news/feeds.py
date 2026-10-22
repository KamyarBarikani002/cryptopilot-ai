"""
منابع خبر و فاندامنتال بدون نیاز به کلید API.

- سرخط خبرهای سایت‌های خبری کریپتو (RSS): CoinDesk، Cointelegraph، Decrypt،
  Bitcoin Magazine، CryptoSlate
- اطلاعیه‌های خود کوکوین: ارزهای تازه لیست‌شده و ارزهایی که حذف می‌شوند
- تقویم اخبار اقتصادی مهم آمریکا در این هفته (CPI، نرخ بهره، اشتغال و ...)
- ارزهای داغ CoinGecko

هر منبع جدا با try/except خوانده می‌شود: اگر یکی در دسترس نبود، بقیه کار می‌کنند.
نتیجه ۱۰ دقیقه در حافظه می‌ماند تا هر اسکن دوباره همه را نگیرد.
"""

import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

from src.news.sentiment import mentioned_coins, sentiment_score

REQUEST_TIMEOUT = 10
CACHE_SECONDS = 600
USER_AGENT = {"User-Agent": "Mozilla/5.0 (CryptoPilotAI news reader)"}

RSS_FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "Bitcoin Magazine": "https://bitcoinmagazine.com/.rss/full/",
    "CryptoSlate": "https://cryptoslate.com/feed/",
}

KUCOIN_ANNOUNCEMENTS_URL = "https://api.kucoin.com/api/v3/announcements"
MACRO_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
COINGECKO_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"

_cache = {"at": 0.0, "value": None}
_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc)


def _parse_time(text):

    if not text:
        return None

    text = text.strip()

    try:
        value = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _strip_tags(text):
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def parse_feed(xml_text, source):

    """RSS 2.0 یا Atom -> [{source, title, link, published, summary}]"""

    items = []
    root = ET.fromstring(xml_text)

    for node in root.iter():

        tag = node.tag.split("}")[-1]

        if tag not in ("item", "entry"):
            continue

        def child(*names):
            # توجه: Element بدون فرزند در if/or «False» است، پس با is None چک می‌کنیم
            for name in names:
                for c in node:
                    if c.tag.split("}")[-1] == name:
                        return c
            return None

        title = child("title")
        link = child("link")
        date = child("pubDate", "published", "updated")
        summary = child("description", "summary")

        link_value = None
        if link is not None:
            link_value = (link.text or "").strip() or link.attrib.get("href")

        def text_of(element):
            # متن کامل، حتی اگر داخلش تگ HTML باشد (مثل <b>)
            return "".join(element.itertext()) if element is not None else ""

        items.append({
            "source": source,
            "title": re.sub(r"\s+", " ", _strip_tags(text_of(title))),
            "link": link_value,
            "published": _parse_time(date.text if date is not None else None),
            "summary": re.sub(r"\s+", " ", _strip_tags(text_of(summary)))[:300],
        })

    return items


def fetch_headlines(max_age_hours=48):

    headlines, errors = [], []
    cutoff = _now() - timedelta(hours=max_age_hours)

    for source, url in RSS_FEEDS.items():
        try:
            response = requests.get(url, headers=USER_AGENT, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            for item in parse_feed(response.content, source):
                if item["title"] and (item["published"] is None or item["published"] >= cutoff):
                    headlines.append(item)
        except Exception as error:
            errors.append(source + ": " + type(error).__name__)

    headlines.sort(key=lambda h: h["published"] or cutoff, reverse=True)

    return headlines, errors


def fetch_kucoin_announcements(ann_type, page_size=30):

    response = requests.get(
        KUCOIN_ANNOUNCEMENTS_URL,
        params={"annType": ann_type, "lang": "en_US", "pageSize": page_size, "currentPage": 1},
        timeout=REQUEST_TIMEOUT,
    )
    payload = response.json()
    items = (payload.get("data") or {}).get("items") or []

    return [
        {
            "title": item.get("annTitle", ""),
            "url": item.get("annUrl"),
            "time": datetime.fromtimestamp(int(item.get("cTime", 0)) / 1000, tz=timezone.utc)
            if item.get("cTime") else None,
            "type": ann_type,
        }
        for item in items
    ]


def fetch_macro_events():

    """رویدادهای اقتصادی آمریکا با اثر زیاد در این هفته."""

    response = requests.get(MACRO_CALENDAR_URL, headers=USER_AGENT, timeout=REQUEST_TIMEOUT)
    events = []

    for item in response.json():
        if item.get("country") != "USD" or item.get("impact") != "High":
            continue
        when = _parse_time(item.get("date"))
        if when is None:
            continue
        events.append({
            "title": item.get("title", ""),
            "time": when,
            "forecast": item.get("forecast") or "",
            "previous": item.get("previous") or "",
        })

    events.sort(key=lambda e: e["time"])
    return events


def fetch_trending():

    response = requests.get(COINGECKO_TRENDING_URL, headers=USER_AGENT, timeout=REQUEST_TIMEOUT)
    coins = response.json().get("coins") or []

    return [
        {"symbol": (c.get("item") or {}).get("symbol", "").upper(),
         "name": (c.get("item") or {}).get("name", "")}
        for c in coins
    ]


def build_news_context(force=False):

    """
    همه‌ی منابع، با کش ۱۰ دقیقه‌ای. خروجی:
    headlines (با sentiment و coins)، coin_scores ({BTC: امتیاز ۲۴ ساعت اخیر})،
    delistings / new_listings (اطلاعیه‌های کوکوین)، macro_events، trending، errors
    """

    with _lock:
        if not force and _cache["value"] is not None and time.time() - _cache["at"] < CACHE_SECONDS:
            return _cache["value"]

    errors = []

    headlines, feed_errors = fetch_headlines()
    errors += feed_errors

    day_ago = _now() - timedelta(hours=24)
    coin_scores = {}

    for item in headlines:
        text = item["title"] + " " + item["summary"]
        item["sentiment"] = sentiment_score(text)
        item["coins"] = sorted(mentioned_coins(item["title"]))
        if item["published"] is None or item["published"] >= day_ago:
            for coin in item["coins"]:
                coin_scores[coin] = coin_scores.get(coin, 0) + item["sentiment"]

    announcements = {}
    for ann_type in ("delistings", "new-listings"):
        try:
            announcements[ann_type] = fetch_kucoin_announcements(ann_type)
        except Exception as error:
            announcements[ann_type] = []
            errors.append("KuCoin " + ann_type + ": " + type(error).__name__)

    month_ago = _now() - timedelta(days=30)
    delisted = set()
    for ann in announcements["delistings"]:
        if ann["time"] is None or ann["time"] >= month_ago:
            delisted |= mentioned_coins(ann["title"], include_short=True)

    try:
        macro_events = fetch_macro_events()
    except Exception as error:
        macro_events = []
        errors.append("تقویم اقتصادی: " + type(error).__name__)

    try:
        trending = fetch_trending()
    except Exception as error:
        trending = []
        errors.append("CoinGecko: " + type(error).__name__)

    context = {
        "fetched_at": _now(),
        "headlines": headlines,
        "coin_scores": coin_scores,
        "delistings": announcements["delistings"],
        "new_listings": announcements["new-listings"],
        "delisted_coins": delisted,
        "macro_events": macro_events,
        "trending": trending,
        "errors": errors,
    }

    with _lock:
        _cache["value"], _cache["at"] = context, time.time()

    return context


def empty_news_context():

    return {
        "fetched_at": _now(), "headlines": [], "coin_scores": {}, "delistings": [],
        "new_listings": [], "delisted_coins": set(), "macro_events": [], "trending": [],
        "errors": [],
    }


def macro_risk_now(context, before_minutes=120, after_minutes=60, now=None):

    """رویداد اقتصادی مهمی که در ۲ ساعت آینده است یا کمتر از ۱ ساعت پیش منتشر شده."""

    now = now or _now()

    for event in context.get("macro_events", []):
        if now - timedelta(minutes=after_minutes) <= event["time"] <= now + timedelta(minutes=before_minutes):
            return event

    return None
