import time

import streamlit as st

from src.auth import require_login

require_login()

from config.settings import FUTURES_TAKER_FEE_PERCENT, PROJECT_NAME, REWARD_RISK_RATIO  # noqa: E402
from src.futures.backtest import equity_curve, split_halves, summarize  # noqa: E402
from src.futures.backtest_job import BacktestJob  # noqa: E402
from src.futures.portfolio_sim import simulate_account  # noqa: E402
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
def _job(code_version):
    # یک کار مشترک برای کل سرور؛ نتیجه با قطع و وصل شدن مرورگر از بین نمی‌رود.
    # code_version: بعد از هر دیپلوی کد جدید، یک کار تازه با کد جدید ساخته شود
    return BacktestJob()


job = _job(str(id(BacktestJob)))
state = job.snapshot()

with st.form("backtest_form"):

    scan_all = st.checkbox(
        "همه‌ی ارزهای فیوچرز کوکوین (۴۰۰+، حدود ۱۰ دقیقه)", value=True,
        help="اگر خاموش باشد، فقط پرحجم‌ترین‌ها به تعداد انتخاب‌شده بررسی می‌شوند."
    )
    columns = st.columns(4)
    top_n = columns[0].slider("یا فقط چند ارز پرحجم", 5, 100, 30, step=5)
    days = columns[1].slider("چند روز گذشته", 30, 180, 180, step=30)
    max_hold = columns[2].slider("حداکثر نگه‌داری (ساعت)", 12, 168, 72, step=12)
    use_funding = columns[3].checkbox("فیلتر فاندینگ تاریخی", value=True)
    run = st.form_submit_button(
        "▶️ اجرای بک‌تست", type="primary", disabled=state["status"] == "running"
    )

if run:
    job.start(
        {"top_n": 0 if scan_all else top_n, "days": days, "max_hold": max_hold, "use_funding": use_funding},
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

def _equity_svg(points, width=900, height=220, pad=28):

    """
    منحنی سرمایه به شکل SVG ساده. st.line_chart روی Streamlit Cloud (پایتون
    3.14) خطای TypeError می‌داد، این راه به هیچ کتابخانه‌ی نموداری وابسته نیست.
    """

    values = [0.0] + [p["equity_r"] for p in points]
    low, high = min(values + [0.0]), max(values + [0.0])
    span = (high - low) or 1.0

    def xy(k, v):
        x = pad + (width - 2 * pad) * k / max(len(values) - 1, 1)
        y = pad + (height - 2 * pad) * (high - v) / span
        return round(x, 1), round(y, 1)

    line = " ".join("%s,%s" % xy(k, v) for k, v in enumerate(values))
    zero_y = xy(0, 0.0)[1]
    color = "#16a34a" if values[-1] >= 0 else "#dc2626"

    return (
        '<svg viewBox="0 0 %d %d" style="width:100%%;height:auto;direction:ltr">' % (width, height)
        + '<line x1="%d" x2="%d" y1="%s" y2="%s" stroke="#9ca3af" stroke-dasharray="4 4"/>' % (pad, width - pad, zero_y, zero_y)
        + '<polyline fill="none" stroke="%s" stroke-width="2.5" points="%s"/>' % (color, line)
        + '<text x="%d" y="%d" font-size="13" fill="#6b7280">%+.1fR</text>' % (pad, pad - 8, high)
        + '<text x="%d" y="%d" font-size="13" fill="#6b7280">%+.1fR</text>' % (pad, height - 6, low)
        + '<text x="%d" y="%d" font-size="13" fill="#6b7280" text-anchor="end">%s → %s (%d معامله)</text>' % (
            width - pad, height - 6, points[0]["time"][:10], points[-1]["time"][:10], len(points))
        + "</svg>"
    )


st.subheader("💼 حساب واقعی با مدیریت سرمایه")
st.caption(
    "همه‌ی معاملات همه‌ی ارزها روی یک حساب و به ترتیب زمان: ریسک هر معامله درصدی "
    "از سرمایه‌ی همان لحظه (سود مرکب)، و در هر روز (UTC) مجموع «زیان امروز + ریسک "
    "پوزیشن‌های باز» از سقف ضرر روزانه بیشتر نمی‌شود؛ معامله‌ای که سقف را رد کند "
    "گرفته نمی‌شود."
)

labels = [label for label, _ in report["results"]]
account_columns = st.columns(4)
chosen = account_columns[0].selectbox("استراتژی", labels)
risk_percent = account_columns[1].number_input("ریسک هر معامله (٪)", 0.1, 3.0, 0.5, 0.1)
daily_limit = account_columns[2].number_input("سقف ضرر روزانه (٪)", 0.5, 5.0, 1.5, 0.1)
max_open = account_columns[3].number_input("حداکثر پوزیشن باز همزمان", 1, 10, 3, 1)

chosen_trades = dict(report["results"])[chosen]
account = simulate_account(chosen_trades, risk_percent, daily_limit, int(max_open))

metric_columns = st.columns(5)
metric_columns[0].metric("میانگین سود ماهانه", format(account["avg_month_percent"], ".1f") + "٪")
metric_columns[1].metric(
    "ماه‌های ≥ ۱۰٪", str(account["months_at_least_10"]) + " از " + str(account["full_months"])
)
metric_columns[2].metric("بدترین ماه", format(account["worst_month_percent"], ".1f") + "٪")
metric_columns[3].metric("بدترین روز", format(account["worst_day_percent"], ".2f") + "٪")
metric_columns[4].metric("بیشترین افت سرمایه", format(account["max_drawdown_percent"], ".1f") + "٪")

st.caption(
    "معاملات گرفته‌شده: " + str(account["taken"]) + " — ردشده به‌خاطر سقف ضرر روزانه: "
    + str(account["skipped_daily_limit"]) + " — ردشده به‌خاطر سقف پوزیشن باز: "
    + str(account["skipped_max_open"]) + ". ماه اول و آخر چون ناقص‌اند در میانگین حساب نشده‌اند."
)

r_per_month = sum(t["r"] for t in chosen_trades) / (report["settings"]["days"] / 30) if chosen_trades else 0
if r_per_month > 0:
    st.info(
        "این استراتژی در این دوره به‌طور متوسط ماهی حدود " + format(r_per_month, ".1f")
        + "R ساخته است. برای ۱۰٪ در ماه با همین تعداد و کیفیت سیگنال، ریسک هر "
        "معامله باید حدود " + format(10 / r_per_month, ".1f") + "٪ باشد"
        + (" — بیشتر از سقف ضرر روزانه‌ی تو، پس با این قانون فقط با سیگنال‌های "
           "بیشتر (ارزهای بیشتر یا شرط‌های بازتر) قابل رسیدن است."
           if 10 / r_per_month > daily_limit else ".")
    )
else:
    st.warning("این استراتژی در این دوره سود خالص نساخته است.")

st.dataframe(
    [{"ماه": m["month"], "سود/زیان (٪)": m["return_percent"]} for m in account["months"]],
    use_container_width=True, hide_index=True,
)

label, main_trades = report["results"][0]

if main_trades:

    st.subheader("منحنی سرمایه — " + label)
    st.markdown(_equity_svg(equity_curve(main_trades)), unsafe_allow_html=True)

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
