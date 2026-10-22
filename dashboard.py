import time
from datetime import datetime

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config.settings import (
    INITIAL_CAPITAL,
    PROJECT_NAME,
    SCAN_TOP_N,
    SIGNAL_STRATEGY,
    SIGNAL_STRATEGY_HAS_PROVEN_EDGE,
    BREAKEVEN_AT_R,
    FUTURES_TAKER_FEE_PERCENT,
)
from src.futures.strategy import STRATEGY_TITLES
from src.futures.scanner import scan_market
from src.futures.demo_data import (
    demo_top_symbols,
    demo_klines,
    demo_funding_rate,
    demo_open_interest_trend,
    demo_fear_greed_index,
    demo_tick_size,
    demo_turnover_24h
)
from src.price_format import format_price
from src.futures.futures_market_data import get_futures_prices, get_futures_klines_range
from src.news.feeds import build_news_context, empty_news_context
from src.exchange_health import check_kucoin_connectivity
from src.ui_common import render_storage_status
from src.futures.risk_budget import daily_budget
from src.futures.signal_tracker import (
    record_new_signals,
    update_open_signals,
    load_history,
    calculate_pnl_percent,
    get_stats
)


from src.auth import require_login
from src.panel_settings_store import (
    load_panel_settings,
    save_panel_settings,
    DEFAULT_PANEL_SETTINGS as _DEFAULT_PANEL_SETTINGS
)

require_login()


st.set_page_config(
    page_title=PROJECT_NAME + " - اسکنر فیوچرز",
    page_icon="📊",
    layout="wide"
)

# چیدمان راست‌به‌چپ برای متن فارسی (استریم‌لیت به‌صورت پیش‌فرض از این پشتیبانی نمی‌کند)
st.markdown(
    """
    <style>
    .stApp, .stMarkdown, .stDataFrame, [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    [data-testid="stMetricValue"] {
        direction: ltr;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📊 " + PROJECT_NAME + " — دستیار سرمایه‌گذاری فیوچرز")

st.caption(
    "استراتژی فعلی: «" + STRATEGY_TITLES[SIGNAL_STRATEGY] + "». حد سود با نسبت "
    "دست‌کم ۱ به ۲ بعد از کارمزد. فاندینگ، Open Interest و ترس‌وطمع در امتیاز "
    "اطمینان اثر دارند. عملکرد روی داده‌ی گذشته در صفحه‌ی Backtest. تضمینی برای "
    "سود وجود ندارد و معامله را خودتان دستی انجام می‌دهید."
)


if "panel_settings" not in st.session_state:
    st.session_state.panel_settings = load_panel_settings()

_saved = st.session_state.panel_settings


with st.sidebar:

    st.header("تنظیمات اسکن")

    demo_mode = st.checkbox(
        "حالت آزمایشی (داده نمایشی، بدون اتصال به کوکوین)",
        value=_saved["demo_mode"],
        help="برای دیدن ظاهر پنل بدون اینترنت یا برای تست سریع."
    )

    scan_all = st.checkbox(
        "همه‌ی ارزهای فیوچرز کوکوین",
        value=int(_saved["top_n"]) == 0,
        help="همه‌ی قراردادهای دائمی USDT کوکوین (۴۰۰+). اسکن حدود یک دقیقه طول می‌کشد."
    )

    top_n_choice = st.slider(
        "یا فقط چند ارز پرحجم؟",
        min_value=5,
        max_value=100,
        value=int(_saved["top_n"]) or 30,
        step=5,
        disabled=scan_all
    )

    top_n = 0 if scan_all else top_n_choice

    capital = st.number_input(
        "سرمایه فرضی برای محاسبه حجم پوزیشن ($)",
        min_value=10,
        value=int(_saved["capital"]),
        step=10
    )

    risk_percent = st.number_input(
        "ریسک هر معامله (٪ سرمایه)",
        min_value=0.1, max_value=3.0, step=0.1,
        value=float(_saved["risk_percent"]),
        help="اگر حد ضرر بخورد، این درصد از سرمایه از دست می‌رود. حجم پوزیشن از روی همین حساب می‌شود."
    )

    daily_loss_limit = st.number_input(
        "سقف ضرر روزانه (٪ سرمایه)",
        min_value=0.5, max_value=5.0, step=0.1,
        value=float(_saved["daily_loss_limit"]),
        help="مجموع زیان امروز + ریسک پوزیشن‌های باز از این بیشتر نمی‌شود."
    )

    scan_clicked = st.button(
        "🔄 اسکن بازار",
        type="primary",
        use_container_width=True
    )

    health_clicked = st.button(
        "🩺 تست اتصال به کوکوین",
        use_container_width=True,
        help="بررسی می‌کند کدام منبع داده (اسپات، فیوچرز، Open Interest) از روی این سرور جواب می‌دهد."
    )

    st.divider()

    auto_refresh_enabled = st.checkbox(
        "تازه‌سازی خودکار",
        value=_saved["auto_refresh_enabled"],
        help="تا وقتی این تب باز باشد، پنل خودش هر چند دقیقه یک‌بار دوباره اسکن می‌کند."
    )

    refresh_minutes = st.selectbox(
        "هر چند دقیقه یک‌بار؟",
        [5, 15, 30, 60],
        index=[5, 15, 30, 60].index(_saved["refresh_minutes"]) if _saved["refresh_minutes"] in [5, 15, 30, 60] else 1,
        disabled=not auto_refresh_enabled
    )

    # تنظیمات فعلی رو ذخیره می‌کنیم تا دفعه بعد که پنل باز می‌شود از همین‌جا ادامه بدهد
    current_settings = {
        "demo_mode": demo_mode,
        "top_n": top_n,
        "capital": int(capital),
        "auto_refresh_enabled": auto_refresh_enabled,
        "refresh_minutes": refresh_minutes,
        "risk_percent": float(risk_percent),
        "daily_loss_limit": float(daily_loss_limit),
    }

    if current_settings != st.session_state.panel_settings:
        st.session_state.panel_settings = current_settings
        save_panel_settings(current_settings)


if not SIGNAL_STRATEGY_HAS_PROVEN_EDGE:
    st.warning(
        "⚠️ استراتژی فعلی در بک‌تست ۱۸۰ روزه با داده‌ی کامل کوکوین سود خالص نداشته "
        "است (جزئیات در صفحه‌ی Backtest). سیگنال‌ها را فعلاً فقط برای آزمایش و ثبت "
        "در تاریخچه استفاده کن، نه برای معامله‌ی واقعی."
    )

budget = daily_budget(load_history(), risk_percent, daily_loss_limit)

with st.sidebar:
    st.caption(
        "🛡️ بودجه‌ی ضرر امروز: " + str(budget["used_percent"]) + "٪ زیان + "
        + str(budget["open_risk_percent"]) + "٪ ریسک باز از سقف " + str(daily_loss_limit)
        + "٪ — امروز " + str(budget["new_trades_allowed"]) + " معامله‌ی تازه‌ی دیگر مجاز است "
        "(اگر همه‌ی سیگنال‌های ثبت‌شده را گرفته باشی)."
    )

if budget["new_trades_allowed"] == 0:
    st.error(
        "🛑 سقف ضرر روزانه پر شده (" + str(daily_loss_limit) + "٪). طبق قانون مدیریت "
        "سرمایه‌ات امروز معامله‌ی تازه باز نکن؛ سیگنال‌ها فقط برای اطلاع نشان داده می‌شوند."
    )


if "scan_result" not in st.session_state:
    st.session_state.scan_result = None
    st.session_state.scan_error = None
    st.session_state.last_scan_time = None


# هر ۳۰ ثانیه یک‌بار اسکریپت رو دوباره اجرا می‌کند تا زمان بررسی شود؛ خودش
# باعث اسکن جدید نمی‌شود، فقط شرط زیر (should_auto_scan) این کار رو می‌کند
if auto_refresh_enabled:
    st_autorefresh(interval=30_000, key="autorefresh_ticker")

should_auto_scan = False

if auto_refresh_enabled:

    if st.session_state.last_scan_time is None:
        should_auto_scan = True
    elif time.time() - st.session_state.last_scan_time >= refresh_minutes * 60:
        should_auto_scan = True


if scan_clicked or should_auto_scan:

    with st.spinner("در حال بررسی بازار..."):

        try:

            if demo_mode:

                result = scan_market(
                    top_n=top_n or None,
                    capital=capital,
                    symbol_fetcher=demo_top_symbols,
                    kline_fetcher=demo_klines,
                    funding_fetcher=demo_funding_rate,
                    oi_fetcher=demo_open_interest_trend,
                    fear_greed_fetcher=demo_fear_greed_index,
                    tick_size_fetcher=demo_tick_size,
                    risk_percent=risk_percent,
                    turnover_fetcher=demo_turnover_24h,
                    news_fetcher=empty_news_context
                )

            else:

                result = scan_market(
                    top_n=top_n or None,
                    capital=capital,
                    risk_percent=risk_percent
                )

                # ثبت/به‌روزرسانی تاریخچه فقط برای اسکن واقعی انجام می‌شود؛
                # حالت آزمایشی هیچ‌وقت به فایل تاریخچه واقعی دست نمی‌زند
                record_new_signals(result["longs"] + result["shorts"])
                _now_ms = int(time.time() * 1000)
                update_open_signals(
                    get_futures_prices,
                    candle_fetcher=lambda symbol, from_ms: get_futures_klines_range(
                        symbol, "1h", from_ms, _now_ms
                    ),
                    breakeven_at_r=BREAKEVEN_AT_R,
                    fee_percent=FUTURES_TAKER_FEE_PERCENT,
                )

            st.session_state.scan_result = result
            st.session_state.scan_error = None
            st.session_state.last_scan_time = time.time()

        except Exception as error:

            st.session_state.scan_result = None
            st.session_state.scan_error = str(error)
            st.session_state.last_scan_time = time.time()


if auto_refresh_enabled and st.session_state.last_scan_time:

    last_scan_label = datetime.fromtimestamp(
        st.session_state.last_scan_time
    ).strftime("%H:%M:%S")

    next_scan_in = max(
        0,
        int(refresh_minutes * 60 - (time.time() - st.session_state.last_scan_time))
    )

    st.caption(
        "🔁 تازه‌سازی خودکار فعال — آخرین اسکن: ساعت " + last_scan_label +
        " | اسکن بعدی تا " + str(next_scan_in) + " ثانیه دیگر "
        "(این تب باید باز بماند)"
    )


render_storage_status()


if health_clicked:

    with st.spinner("در حال تست اتصال به کوکوین..."):
        health_rows = check_kucoin_connectivity()

    if all(row["وضعیت"] == "✅" for row in health_rows):
        st.success("همه‌ی منابع داده‌ی کوکوین از روی این سرور در دسترس هستند.")
    else:
        st.error("بعضی از منابع داده‌ی کوکوین از روی این سرور جواب نمی‌دهند:")

    st.dataframe(health_rows, use_container_width=True, hide_index=True)


if st.session_state.scan_error:

    st.error(
        "خطا در اسکن بازار: " + st.session_state.scan_error +
        "\n\nاگر اینترنت ندارید یا کوکوین در دسترس نیست، از نوار کناری "
        "«حالت آزمایشی» رو فعال کنید."
    )


result = st.session_state.scan_result

if result is not None and "fear_greed_index" in result:

    fg_value = result["fear_greed_index"]

    if fg_value <= 25:
        fg_label = "ترس شدید"
    elif fg_value <= 45:
        fg_label = "ترس"
    elif fg_value <= 55:
        fg_label = "خنثی"
    elif fg_value <= 75:
        fg_label = "طمع"
    else:
        fg_label = "طمع شدید"

    st.caption("🌡️ شاخص ترس‌وطمع کل بازار: **" + str(fg_value) + "** (" + fg_label + ")")

if result is not None and result.get("macro_event"):
    _event = result["macro_event"]
    st.warning(
        "📅 خبر مهم اقتصادی آمریکا نزدیک است: **" + _event["title"] + "** ساعت "
        + _event["time"].strftime("%H:%M UTC")
        + " — در این بازه سیگنال جدید داده نمی‌شود (نوسان غیرقابل‌پیش‌بینی)."
    )


tab_long, tab_short, tab_history, tab_news = st.tabs([
    "📈 فرصت‌های Long" + (" (" + str(len(result["longs"])) + ")" if result else ""),
    "📉 فرصت‌های Short" + (" (" + str(len(result["shorts"])) + ")" if result else ""),
    "📊 تاریخچه و دقت سیگنال‌ها",
    "📰 اخبار و رویدادها",
])


LOW_VOLUME_USD = 1_000_000


def _volume_label(turnover):

    """حجم معاملات ۲۴ ساعته؛ زیر ۱ میلیون دلار هشدار می‌دهد (اسلیپیج و اسپرد زیاد)."""

    if turnover >= 1_000_000_000:
        text = format(turnover / 1_000_000_000, ".1f") + "B$"
    elif turnover >= 1_000_000:
        text = format(turnover / 1_000_000, ".1f") + "M$"
    else:
        text = format(turnover / 1_000, ".0f") + "K$"

    return ("⚠️ کم‌حجم " if turnover < LOW_VOLUME_USD else "") + text


def render_table(opportunities, direction_label):

    if not opportunities:
        st.info("در حال حاضر فرصت " + direction_label + " واضحی پیدا نشد.")
        return

    rows = []

    for o in opportunities:

        rows.append({
            "ارز": o["symbol"],
            "اطمینان (۰-۱۰۰)": o["confidence"],
            "قیمت ورود": format_price(o["entry_price"]),
            "حد ضرر": format_price(o["stop_loss_price"]) + "  (-" + str(o["stop_loss_percent"]) + "٪)",
            "حد سود ۱ (بستن نصف)": (
                format_price(o["take_profit_1_price"]) + "  (+" + str(o.get("take_profit_1_percent")) + "٪)"
                if o.get("take_profit_1_price") else "—"
            ),
            "حد سود" + (" ۲ (بقیه)" if o.get("take_profit_1_price") else ""):
                format_price(o["take_profit_price"]) + "  (+" + str(o["take_profit_percent"]) + "٪)",
            "ریسک به ریوارد": "1 : " + format(o["reward_risk_ratio"], ".2f"),
            "اهرم پیشنهادی": str(o["leverage"]) + "x",
            "حجم پوزیشن ($)": o["position_size_usd"],
            "مارجین لازم ($)": o["margin_required_usd"],
            "ریسک ($)": o["risk_amount_usd"],
            "کیفیت ستاپ": o["technical_score"],
            "امتیاز فاندامنتال": o["fundamental_score"],
            "حجم ۲۴ ساعته": _volume_label(o.get("turnover_24h") or 0),
            "ADX": o["adx"],
            "RSI": o["rsi"],
            "فاندینگ (٪)": o["funding_rate_percent"],
            "روند OI (٪)": o["oi_trend_percent"],
            "امتیاز اخبار": o.get("news_score", 0),
            "دلایل تکنیکال": "، ".join(o.get("reasons") or []),
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True
    )


if result is None:

    with tab_long:
        st.info("برای شروع، از نوار کناری روی «اسکن بازار» بزنید.")

    with tab_short:
        st.info("برای شروع، از نوار کناری روی «اسکن بازار» بزنید.")

else:

    st.write("تعداد ارزهای بررسی‌شده: **" + str(result["scanned"]) + "**")

    with tab_long:
        render_table(result["longs"], "Long")

    with tab_short:
        render_table(result["shorts"], "Short")

    if result.get("blocked"):

        with st.expander("🛑 " + str(len(result["blocked"])) + " سیگنال به خاطر خبر/رویداد کنار گذاشته شد"):
            st.table([
                {"ارز": b["symbol"], "جهت": b["direction"], "دلیل": b.get("blocked_reason") or ""}
                for b in result["blocked"]
            ])

    if result["skipped"]:

        with st.expander(str(len(result["skipped"])) + " ارز به دلیل خطا رد شدند"):

            for item in result["skipped"]:
                st.write(item["symbol"], ":", item["error"])


with tab_history:

    st.caption(
        "این تاریخچه فقط از اسکن‌های واقعی (نه حالت آزمایشی) ساخته می‌شود. "
        "هر سیگنالی که ثبت شود، در اسکن‌های بعدی چک می‌شود که آیا قیمت به "
        "حد سود یا حد ضرر رسیده یا نه."
    )

    history = load_history()

    if not history:

        st.info(
            "هنوز هیچ سیگنالی ثبت نشده. بعد از چند بار اسکن واقعی (بدون حالت "
            "آزمایشی)، تاریخچه و درصد دقت این‌جا نمایش داده می‌شود."
        )

    else:

        stats = get_stats(history)

        stat_columns = st.columns(8)

        stat_columns[0].metric("کل سیگنال‌ها", stats["total"])
        stat_columns[1].metric("باز", stats["open"])
        stat_columns[2].metric("بسته‌شده", stats["closed"])
        stat_columns[3].metric("برد کامل", stats["wins"])
        stat_columns[4].metric("فقط پله‌ی اول", stats.get("partials", 0))
        stat_columns[5].metric("سر‌به‌سر", stats.get("breakevens", 0))
        stat_columns[6].metric("باخت", stats["losses"])
        stat_columns[7].metric("بسته‌شده با سود", str(stats.get("profit_rate", stats["win_rate"])) + "%")
        st.caption(
            "برد کامل: به حد سود اصلی رسید. فقط پله‌ی اول (خروج پله‌ای): نصف پوزیشن در "
            "حد سود ۱ با سود بسته شد و بقیه سر‌به‌سر. سر‌به‌سر: بعد از +۱R حد ضرر به "
            "نقطه‌ی ورود رفت و همان‌جا بسته شد. حد ضرر و حد سود روی سقف/کف کندل‌های "
            "۱ ساعته چک می‌شوند."
        )

        st.subheader("سیگنال‌های باز")

        open_records = [r for r in history if r["status"] == "OPEN"]

        if not open_records:
            st.info("هیچ سیگنال بازی وجود ندارد.")
        else:
            st.dataframe(
                [
                    {
                        "ارز": r["symbol"],
                        "جهت": r["direction"],
                        "قیمت ورود": format_price(r["entry_price"]),
                        "حد ضرر": format_price(r["stop_loss_price"])
                        + (" 🔒 سر‌به‌سر" if r.get("initial_stop_price")
                           and r["stop_loss_price"] != r["initial_stop_price"] else ""),
                        "حد سود ۱": format_price(r["take_profit_1_price"]) if r.get("take_profit_1_price") else "—",
                        "حد سود": format_price(r["take_profit_price"]),
                        "زمان باز شدن": r["opened_at"],
                    }
                    for r in open_records
                ],
                use_container_width=True,
                hide_index=True
            )

        st.subheader("سیگنال‌های بسته‌شده (اخیر)")

        closed_records = [
            r for r in history
            if r["status"] in ("WIN", "LOSS", "BREAKEVEN", "PARTIAL", "EXPIRED")
        ]

        closed_records.sort(
            key=lambda r: r["closed_at"] or "",
            reverse=True
        )

        if not closed_records:
            st.info("هنوز هیچ سیگنالی بسته نشده.")
        else:
            st.dataframe(
                [
                    {
                        "ارز": r["symbol"],
                        "جهت": r["direction"],
                        "نتیجه": {"WIN": "✅ برد", "PARTIAL": "🟢 پله‌ی اول", "BREAKEVEN": "⚪ سر‌به‌سر",
                                  "LOSS": "❌ باخت", "EXPIRED": "⌛ منقضی"}.get(r["status"], r["status"]),
                        "قیمت ورود": format_price(r["entry_price"]),
                        "قیمت خروج": format_price(r["closed_price"]),
                        "سود/زیان (٪)": calculate_pnl_percent(r),
                        "زمان بسته شدن": r["closed_at"],
                    }
                    for r in closed_records[:30]
                ],
                use_container_width=True,
                hide_index=True
            )


with tab_news:

    st.caption(
        "منابع بدون کلید: سرخط CoinDesk، Cointelegraph، Decrypt، Bitcoin Magazine و "
        "CryptoSlate، اطلاعیه‌های لیست/حذف کوکوین، تقویم اخبار مهم اقتصادی آمریکا "
        "و ارزهای داغ CoinGecko. هر ۱۰ دقیقه تازه می‌شود. اسکنر سیگنالِ ارزی که "
        "کوکوین حذفش را اعلام کرده، سیگنال خلاف خبرهای خیلی قوی ۲۴ ساعت اخیر، و هر "
        "سیگنالی در ۲ ساعت قبل تا ۱ ساعت بعد از خبر مهم اقتصادی را کنار می‌گذارد."
    )

    if demo_mode:
        st.info("در حالت آزمایشی اخبار گرفته نمی‌شود.")
    else:
        with st.spinner("در حال خواندن اخبار..."):
            try:
                _news = build_news_context()
            except Exception as error:
                _news = None
                st.error("خواندن اخبار ممکن نشد: " + str(error))

        if _news is not None:

            if _news["errors"]:
                st.caption("در دسترس نبود: " + "، ".join(_news["errors"]))

            st.subheader("📅 خبرهای مهم اقتصادی آمریکا (این هفته)")
            if _news["macro_events"]:
                st.table([
                    {"زمان (UTC)": e["time"].strftime("%a %d %b %H:%M"), "رویداد": e["title"],
                     "پیش‌بینی": e["forecast"], "قبلی": e["previous"]}
                    for e in _news["macro_events"]
                ])
            else:
                st.write("رویداد مهمی ثبت نشده.")

            _scores = sorted(_news["coin_scores"].items(), key=lambda kv: kv[1])
            if _scores:
                st.subheader("🧭 حال‌وهوای خبری ارزها (۲۴ ساعت اخیر)")
                st.table([
                    {"ارز": coin, "امتیاز خبر": score,
                     "وضعیت": "🔴 منفی" if score <= -3 else "🟢 مثبت" if score >= 3 else "⚪ خنثی"}
                    for coin, score in (_scores[:8] + [x for x in _scores[-8:] if x not in _scores[:8]])
                ])

            _columns = st.columns(2)
            with _columns[0]:
                st.subheader("🛑 حذف از کوکوین")
                for ann in _news["delistings"][:8]:
                    st.markdown("- [" + ann["title"] + "](" + (ann["url"] or "#") + ")")
                if not _news["delistings"]:
                    st.write("—")
            with _columns[1]:
                st.subheader("🆕 لیست‌های تازه‌ی کوکوین")
                for ann in _news["new_listings"][:8]:
                    st.markdown("- [" + ann["title"] + "](" + (ann["url"] or "#") + ")")
                if not _news["new_listings"]:
                    st.write("—")

            if _news["trending"]:
                st.caption("🔥 داغ در CoinGecko: " + "، ".join(t["symbol"] for t in _news["trending"][:10]))

            st.subheader("📰 آخرین سرخط‌ها")
            st.table([
                {
                    "منبع": h["source"],
                    "زمان (UTC)": h["published"].strftime("%d %b %H:%M") if h["published"] else "",
                    "عنوان": h["title"],
                    "ارزها": " ".join(h.get("coins") or []),
                    "احساس": h.get("sentiment", 0),
                }
                for h in _news["headlines"][:25]
            ])


st.divider()

_DIP_EXPLANATION = (
    "**شرط ورود (خرید افت در روند):**\n\n"
    "- **Long:** قیمت بالای میانگین ۲۰ کندل ۱ ساعته (روند صعودی) ولی RSI زیر "
    "۳۰؛ یعنی یک افت تند داخل روند صعودی.\n"
    "- **Short:** قیمت زیر میانگین ۲۰ کندل (روند نزولی) ولی RSI بالای ۷۰.\n\n"
    "**حد ضرر** بر اساس نوسان اخیر همان ارز (۲ برابر میانگین تغییر ۱۴ کندل "
    "اخیر، بین ۱٫۵٪ تا ۱۵٪)."
)

_PULLBACK_EXPLANATION = (
    "**شرط ورود (پولبک در جهت روند):** روند ۱ و ۴ ساعته هم‌جهت، ADX دست‌کم ۲۰، "
    "اصلاح تا حوالی EMA20 بدون شکستن ساختار، کندل آخر دوباره در جهت روند، و "
    "فاندینگ بیش از حد شلوغ نباشد.\n\n"
    "**حد ضرر** پشت آخرین کف/سقف ۱۰ کندل اخیر (بین ۱ تا ۳ برابر ATR)."
)

with st.expander("ℹ️ سیگنال‌ها چطور ساخته می‌شوند؟"):

    st.markdown(
        (_DIP_EXPLANATION if SIGNAL_STRATEGY == "dip" else _PULLBACK_EXPLANATION)
        + "\n\n**حد سود** طوری که سود خالص بعد از کارمزد ورود و خروج (هر طرف "
        "۰٫۰۶٪) دست‌کم **۲ برابر** زیان خالص باشد. هر دو به گام قیمت همان "
        "قرارداد در کوکوین گرد می‌شوند. فقط کندل‌های بسته‌شده تحلیل می‌شوند.\n\n"
        "**اطمینان (۰ تا ۱۰۰)** فقط برای مرتب کردن است: ۷۵٪ قدرت ستاپ و ۲۵٪ "
        "هم‌جهتی فاندامنتال (فاندینگ، Open Interest، ترس‌وطمع).\n\n"
        "استراتژی در `config/settings.py` (`SIGNAL_STRATEGY`) انتخاب می‌شود؛ "
        "مقایسه‌ی استراتژی‌ها روی داده‌ی گذشته در صفحه‌ی «Backtest»."
    )

st.warning(
    "⚠️ اهرم پیشنهادی یک تخمین محافظه‌کارانه بر اساس فاصله‌ی حد ضرر است، نه "
    "تضمین. قیمت لیکویید واقعی به مارجین نگهداری و کارمزد/فاندینگ صرافی هم "
    "بستگی دارد و ممکن است زودتر از حد ضرر پیش‌بینی‌شده اتفاق بیفتد. اهرم "
    "بالاتر از عدد پیشنهادی، ریسک لیکویید شدن را به‌شدت افزایش می‌دهد. این "
    "ابزار ترکیبی از تحلیل تکنیکال و فاندامنتال ساده است و هیچ تضمینی برای "
    "سود وجود ندارد؛ همیشه پیش از هر معامله خودتان قیمت و بازار را هم بررسی "
    "کنید."
)
