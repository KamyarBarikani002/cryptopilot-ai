import time

import streamlit as st

from src.auth import require_login

require_login()

from config.settings import FUTURES_TAKER_FEE_PERCENT, PROJECT_NAME, REWARD_RISK_RATIO  # noqa: E402
from src.futures.backtest import backtest_symbol, equity_curve, summarize  # noqa: E402
from src.futures.fundamental_engine import get_funding_history  # noqa: E402
from src.futures.futures_market_data import (  # noqa: E402
    get_futures_klines_range,
    get_tick_size,
    get_top_symbols_by_volume,
)
from src.price_format import format_price  # noqa: E402
from src.ui_common import render_storage_status  # noqa: E402

st.set_page_config(page_title=PROJECT_NAME + " - بک‌تست", page_icon="📈", layout="wide")

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
    unsafe_allow_html=True,
)

st.title("📈 بک‌تست سیگنال‌های فیوچرز")

breakeven = 100 / (1 + REWARD_RISK_RATIO)

st.caption(
    "قوانین سیگنال روی کندل‌های ۱ ساعته‌ی گذشته‌ی کوکوین، کندل به کندل اجرا "
    "می‌شوند؛ دقیقاً همان کدی که اسکنر زنده استفاده می‌کند. ورود روی قیمت "
    "بسته‌شدن کندل سیگنال، خروج با حد سود یا حد ضرر (نسبت دست‌کم ۱ به "
    + str(REWARD_RISK_RATIO) + " بعد از کارمزد " + str(FUTURES_TAKER_FEE_PERCENT)
    + "٪). با این نسبت، نرخ برد بالای حدود " + format(breakeven, ".0f")
    + "٪ یعنی سوددهی."
)

render_storage_status()

STRATEGY_VARIANTS = [
    ("نسخه‌ی جدید (پولبک در جهت روند)", "v2", {}),
    ("نسخه‌ی جدید بدون فیلتر روند ۴ ساعته", "v2", {"use_4h_filter": False}),
    ("نسخه‌ی جدید بدون فیلتر ADX", "v2", {"use_adx_filter": False}),
    ("منطق قبلی (MA20 + RSI)", "v1", {}),
]

with st.form("backtest_form"):

    columns = st.columns(4)
    top_n = columns[0].slider("تعداد ارزهای پرحجم", 5, 30, 20, step=5)
    days = columns[1].slider("چند روز گذشته", 30, 180, 90, step=30)
    max_hold = columns[2].slider("حداکثر نگه‌داری (ساعت)", 12, 168, 72, step=12)
    use_funding = columns[3].checkbox("فیلتر فاندینگ تاریخی", value=True)
    run = st.form_submit_button("▶️ اجرای بک‌تست", type="primary")


@st.cache_data(ttl=3600, show_spinner=False)
def _load_symbol(symbol, start_ms, end_ms, with_funding):

    candles = get_futures_klines_range(symbol, "1h", start_ms, end_ms)
    funding = get_funding_history(symbol, start_ms, end_ms) if with_funding else []
    return candles, funding


if run:

    end_ms = int(time.time() // 3600 * 3600 * 1000)
    # ۳۰۰ کندل اضافه برای گرم شدن EMA200 و روند ۴ ساعته
    start_ms = end_ms - (days * 24 + 300) * 3_600_000

    symbols = get_top_symbols_by_volume(top_n)
    progress = st.progress(0.0, text="در حال دانلود تاریخچه از کوکوین...")
    loaded, failed = {}, []

    for k, symbol in enumerate(symbols):
        try:
            loaded[symbol] = _load_symbol(symbol, start_ms, end_ms, use_funding) + (get_tick_size(symbol),)
        except Exception as error:
            failed.append(symbol + ": " + str(error))
        progress.progress((k + 1) / len(symbols), text="دانلود " + symbol)

    progress.progress(1.0, text="در حال اجرای بک‌تست...")

    results = []
    for label, name, params in STRATEGY_VARIANTS:
        trades = []
        for symbol, (candles, funding, tick) in loaded.items():
            trades += backtest_symbol(
                symbol, candles, name, params,
                funding_points=funding if name == "v2" else None,
                min_reward_risk=REWARD_RISK_RATIO, fee_percent=FUTURES_TAKER_FEE_PERCENT,
                max_hold=max_hold, tick_size=tick,
            )
        results.append((label, trades))

    progress.empty()

    st.session_state.backtest = {
        "results": results, "failed": failed, "symbols": list(loaded),
        "days": days, "max_hold": max_hold, "ran_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    }


report = st.session_state.get("backtest")

if not report:
    st.info("تنظیمات بالا را انتخاب کن و «اجرای بک‌تست» را بزن. دانلود تاریخچه حدود یک دقیقه طول می‌کشد.")
    st.stop()

st.caption(
    "اجرا شده در " + report["ran_at"] + " روی " + str(len(report["symbols"])) + " ارز، "
    + str(report["days"]) + " روز گذشته، حداکثر نگه‌داری " + str(report["max_hold"]) + " ساعت."
)

if report["failed"]:
    with st.expander(str(len(report["failed"])) + " ارز دانلود نشد"):
        for line in report["failed"]:
            st.write(line)

summary_rows = []
for label, trades in report["results"]:
    s = summarize(trades)
    summary_rows.append({
        "استراتژی": label,
        "معاملات": s["trades"],
        "برد": s["wins"],
        "باخت": s["losses"],
        "بدون نتیجه (تایم‌اوت)": s["timeouts"],
        "نرخ برد (٪)": s["win_rate"],
        "میانگین هر معامله (R)": s["avg_r"],
        "مجموع (R)": s["total_r"],
        "Profit factor": s["profit_factor"],
        "بیشترین افت (R)": s["max_drawdown_r"],
    })

st.subheader("مقایسه")
st.dataframe(summary_rows, use_container_width=True, hide_index=True)
st.caption(
    "R یعنی مقدار ریسک هر معامله. با ریسک ۱٪ سرمایه در هر معامله، «مجموع ۱۰R» "
    "یعنی حدود ۱۰٪ سود و «بیشترین افت ۵R» یعنی در بدترین دوره حدود ۵٪ افت."
)

label, main_trades = report["results"][0]

if main_trades:

    st.subheader("منحنی سرمایه — " + label)
    st.line_chart(equity_curve(main_trades), x="time", y="equity_r")

    st.subheader("به تفکیک ارز")
    per_symbol = {}
    for t in main_trades:
        per_symbol.setdefault(t["symbol"], []).append(t)
    st.dataframe(
        sorted(
            [
                {"ارز": sym, "معاملات": s["trades"], "نرخ برد (٪)": s["win_rate"], "مجموع (R)": s["total_r"]}
                for sym, s in ((sym, summarize(ts)) for sym, ts in per_symbol.items())
            ],
            key=lambda row: row["مجموع (R)"], reverse=True,
        ),
        use_container_width=True, hide_index=True,
    )

    st.subheader("آخرین معاملات")
    st.dataframe(
        [
            {
                "ارز": t["symbol"], "جهت": t["direction"], "ورود": t["opened"], "خروج": t["closed"],
                "نتیجه": t["result"], "R": t["r"], "قیمت ورود": format_price(t["entry"]),
                "حد ضرر": format_price(t["stop"]), "حد سود": format_price(t["target"]),
            }
            for t in sorted(main_trades, key=lambda t: t["opened"], reverse=True)[:50]
        ],
        use_container_width=True, hide_index=True,
    )

st.warning(
    "⚠️ نتیجه‌ی گذشته تضمین آینده نیست. این بک‌تست لغزش قیمت (slippage) را حساب "
    "نمی‌کند، فقط ارزهایی را می‌بیند که امروز جزو پرحجم‌ها هستند، و Open Interest "
    "و ترس‌وطمع گذشته را در شرط ورود ندارد (فقط فاندینگ)."
)
