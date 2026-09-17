import time
from datetime import datetime

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config.settings import SCAN_TOP_N, INITIAL_CAPITAL, PROJECT_NAME
from src.futures.scanner import scan_market
from src.futures.demo_data import (
    demo_top_symbols,
    demo_klines,
    demo_funding_rate,
    demo_open_interest_trend,
    demo_fear_greed_index
)
from src.futures.futures_market_data import get_futures_prices
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
    "این ابزار سیگنال‌ها را از ترکیب تحلیل تکنیکال (روند + RSI) و تحلیل "
    "فاندامنتال (نرخ فاندینگ، روند Open Interest، شاخص ترس‌وطمع بازار) "
    "می‌سازد؛ تضمینی برای سود وجود ندارد و معامله را خودتان به‌صورت دستی در "
    "صرافی انجام می‌دهید."
)


if "panel_settings" not in st.session_state:
    st.session_state.panel_settings = load_panel_settings()

_saved = st.session_state.panel_settings


with st.sidebar:

    st.header("تنظیمات اسکن")

    demo_mode = st.checkbox(
        "حالت آزمایشی (داده نمایشی، بدون اتصال به بایننس)",
        value=_saved["demo_mode"],
        help="برای دیدن ظاهر پنل بدون اینترنت یا برای تست سریع."
    )

    top_n = st.slider(
        "چند ارز پرحجم فیوچرز بررسی شود؟",
        min_value=5,
        max_value=100,
        value=int(_saved["top_n"]),
        step=5
    )

    capital = st.number_input(
        "سرمایه فرضی برای محاسبه حجم پوزیشن ($)",
        min_value=10,
        value=int(_saved["capital"]),
        step=10
    )

    scan_clicked = st.button(
        "🔄 اسکن بازار",
        type="primary",
        use_container_width=True
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
        "refresh_minutes": refresh_minutes
    }

    if current_settings != st.session_state.panel_settings:
        st.session_state.panel_settings = current_settings
        save_panel_settings(current_settings)


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
                    top_n=top_n,
                    capital=capital,
                    symbol_fetcher=demo_top_symbols,
                    kline_fetcher=demo_klines,
                    funding_fetcher=demo_funding_rate,
                    oi_fetcher=demo_open_interest_trend,
                    fear_greed_fetcher=demo_fear_greed_index
                )

            else:

                result = scan_market(
                    top_n=top_n,
                    capital=capital
                )

                # ثبت/به‌روزرسانی تاریخچه فقط برای اسکن واقعی انجام می‌شود؛
                # حالت آزمایشی هیچ‌وقت به فایل تاریخچه واقعی دست نمی‌زند
                record_new_signals(result["longs"] + result["shorts"])
                update_open_signals(get_futures_prices)

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


if st.session_state.scan_error:

    st.error(
        "خطا در اسکن بازار: " + st.session_state.scan_error +
        "\n\nاگر اینترنت ندارید یا بایننس در دسترس نیست، از نوار کناری "
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


tab_long, tab_short, tab_history = st.tabs([
    "📈 فرصت‌های Long" + (" (" + str(len(result["longs"])) + ")" if result else ""),
    "📉 فرصت‌های Short" + (" (" + str(len(result["shorts"])) + ")" if result else ""),
    "📊 تاریخچه و دقت سیگنال‌ها"
])


def render_table(opportunities, direction_label):

    if not opportunities:
        st.info("در حال حاضر فرصت " + direction_label + " واضحی پیدا نشد.")
        return

    rows = []

    for o in opportunities:

        rows.append({
            "ارز": o["symbol"],
            "امتیاز ترکیبی": o["score"],
            "امتیاز تکنیکال": o["technical_score"],
            "امتیاز فاندامنتال": o["fundamental_score"],
            "فاندینگ (٪)": o["funding_rate_percent"],
            "روند OI (٪)": o["oi_trend_percent"],
            "قیمت ورود": o["entry_price"],
            "حد ضرر": o["stop_loss_price"],
            "حد سود": o["take_profit_price"],
            "اهرم پیشنهادی": str(o["leverage"]) + "x",
            "حجم پوزیشن ($)": o["position_size_usd"],
            "مارجین لازم ($)": o["margin_required_usd"],
            "نوسان (٪)": o["volatility_percent"],
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

        stat_columns = st.columns(6)

        stat_columns[0].metric("کل سیگنال‌ها", stats["total"])
        stat_columns[1].metric("باز", stats["open"])
        stat_columns[2].metric("بسته‌شده", stats["closed"])
        stat_columns[3].metric("برد", stats["wins"])
        stat_columns[4].metric("باخت", stats["losses"])
        stat_columns[5].metric("نرخ برد", str(stats["win_rate"]) + "%")

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
                        "قیمت ورود": r["entry_price"],
                        "حد ضرر": r["stop_loss_price"],
                        "حد سود": r["take_profit_price"],
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
            if r["status"] in ("WIN", "LOSS", "EXPIRED")
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
                        "نتیجه": r["status"],
                        "قیمت ورود": r["entry_price"],
                        "قیمت خروج": r["closed_price"],
                        "سود/زیان (٪)": calculate_pnl_percent(r),
                        "زمان بسته شدن": r["closed_at"],
                    }
                    for r in closed_records[:30]
                ],
                use_container_width=True,
                hide_index=True
            )


st.divider()

with st.expander("ℹ️ امتیاز ترکیبی چطور محاسبه می‌شود؟"):

    st.markdown(
        "امتیاز نهایی هر ارز (که تصمیم Long/Short بر اساس آن گرفته می‌شود) "
        "ترکیبی وزن‌دار از دو بخش است:\n\n"
        "- **امتیاز تکنیکال (وزن ۶۰٪):** بر اساس روند قیمت نسبت به میانگین "
        "متحرک و RSI.\n"
        "- **امتیاز فاندامنتال (وزن ۴۰٪):** بر اساس نرخ فاندینگ (پوزیشن‌های "
        "شلوغ لانگ/شورت)، روند Open Interest (تایید یا تضعیف روند با ورود/"
        "خروج پول) و شاخص ترس‌وطمع کل بازار.\n\n"
        "این وزن‌ها در `config/settings.py` قابل تغییرند "
        "(`TECHNICAL_WEIGHT` و `FUNDAMENTAL_WEIGHT`)."
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
