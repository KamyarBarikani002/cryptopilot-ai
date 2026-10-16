import time

import pandas as pd
import streamlit as st

from src.auth import require_login

require_login()

from config.settings import FUTURES_TAKER_FEE_PERCENT, PROJECT_NAME, REWARD_RISK_RATIO  # noqa: E402
from src.futures.backtest import equity_curve, split_halves, summarize  # noqa: E402
from src.futures.backtest_job import BacktestJob  # noqa: E402
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

@st.cache_resource
def _job():
    # یک کار مشترک برای کل سرور؛ نتیجه با قطع و وصل شدن مرورگر از بین نمی‌رود
    return BacktestJob()


job = _job()
state = job.snapshot()

with st.form("backtest_form"):

    columns = st.columns(4)
    top_n = columns[0].slider("تعداد ارزهای پرحجم", 5, 30, 30, step=5)
    days = columns[1].slider("چند روز گذشته", 30, 180, 180, step=30)
    max_hold = columns[2].slider("حداکثر نگه‌داری (ساعت)", 12, 168, 72, step=12)
    use_funding = columns[3].checkbox("فیلتر فاندینگ تاریخی", value=True)
    run = st.form_submit_button(
        "▶️ اجرای بک‌تست", type="primary", disabled=state["status"] == "running"
    )

if run:
    job.start(
        {"top_n": top_n, "days": days, "max_hold": max_hold, "use_funding": use_funding},
        {
            "symbols": get_top_symbols_by_volume,
            "klines": get_futures_klines_range,
            "funding": get_funding_history,
            "tick": get_tick_size,
        },
    )
    state = job.snapshot()

if state["status"] == "running":
    st.progress(state["progress"], text=state["message"])
    st.caption("بک‌تست روی سرور در حال اجراست؛ می‌توانی صفحه را ببندی و بعداً برگردی.")
    time.sleep(2)
    st.rerun()

if state["status"] == "error":
    st.error("بک‌تست با خطا متوقف شد:\n\n" + str(state["error"]))

report = state["report"]


if not report:
    st.info("تنظیمات بالا را انتخاب کن و «اجرای بک‌تست» را بزن. دانلود تاریخچه چند دقیقه طول می‌کشد.")
    st.stop()

st.caption(
    "آخرین اجرا: " + report["ran_at"] + " روی " + str(len(report["symbols"])) + " ارز، "
    + str(report["settings"]["days"]) + " روز گذشته، حداکثر نگه‌داری "
    + str(report["settings"]["max_hold"]) + " ساعت (" + str(report["seconds"]) + " ثانیه طول کشید)."
)

if report["failed"]:
    with st.expander(str(len(report["failed"])) + " ارز دانلود نشد"):
        for line in report["failed"]:
            st.write(line)

with st.expander("زمان دانلود هر ارز (ثانیه)"):
    st.json(report["timings"])

summary_rows = []
for label, trades in report["results"]:
    s = summarize(trades)
    first, second = (summarize(half) for half in split_halves(trades, report.get("middle", "")))
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
        "نیمه‌ی اول (R)": first["total_r"],
        "نیمه‌ی دوم (R)": second["total_r"],
    })

st.subheader("مقایسه")
st.dataframe(summary_rows, use_container_width=True, hide_index=True)
st.caption(
    "«نیمه‌ی اول/دوم» نتیجه را جدا برای دو نیمه‌ی دوره نشان می‌دهد: استراتژی‌ای "
    "که فقط در یک نیمه سود داده، احتمالاً شانسی بوده. "
    "R یعنی مقدار ریسک هر معامله. با ریسک ۱٪ سرمایه در هر معامله، «مجموع ۱۰R» "
    "یعنی حدود ۱۰٪ سود و «بیشترین افت ۵R» یعنی در بدترین دوره حدود ۵٪ افت."
)

label, main_trades = report["results"][0]

if main_trades:

    st.subheader("منحنی سرمایه — " + label)
    st.line_chart(pd.DataFrame(equity_curve(main_trades)), x="time", y="equity_r")

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
