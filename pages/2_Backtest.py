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

    top_columns = st.columns(2)
    universe_choice = top_columns[0].radio(
        "کدام ارزها؟",
        ["۲۰۰ ارز پرحجم", "۱۰۰ ارز پرحجم", "۳۰ ارز پرحجم", "همه‌ی ارزهای کوکوین (۵۰۰+)"],
        help="بک‌تست قبلی نشان داد ارزهای خیلی کم‌حجم نتیجه را خراب می‌کنند؛ ۲۰۰ پرحجم تعادل خوبی است.",
    )
    variant_choice = top_columns[1].radio(
        "چه چیزهایی مقایسه شود؟",
        ["جست‌وجوی گسترده (۱۳ حالت، کندتر)", "مقایسه‌ی سریع (۴ حالت)"],
    )
    columns = st.columns(4)
    columns[0].caption("بازه‌ی زمانی و نگه‌داری:")
    days = columns[1].slider("چند روز گذشته", 30, 180, 180, step=30)
    max_hold = columns[2].slider("حداکثر نگه‌داری (ساعت)", 12, 168, 72, step=12)
    use_funding = columns[3].checkbox("فیلتر فاندینگ تاریخی", value=True)
    run = st.form_submit_button(
        "▶️ اجرای بک‌تست", type="primary", disabled=state["status"] == "running"
    )

if run:
    job.start(
        {
            "top_n": {"۲۰۰ ارز پرحجم": 200, "۱۰۰ ارز پرحجم": 100, "۳۰ ارز پرحجم": 30}.get(universe_choice, 0),
            "days": days, "max_hold": max_hold, "use_funding": use_funding,
            "variant_set": "research" if variant_choice.startswith("جست‌وجو") else "quick",
        },
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
st.table(summary_rows)
st.caption(
    "«نیمه‌ی اول/دوم» نتیجه را جدا برای دو نیمه‌ی دوره نشان می‌دهد: استراتژی‌ای "
    "که فقط در یک نیمه سود داده، احتمالاً شانسی بوده. "
    "R یعنی مقدار ریسک هر معامله. با ریسک ۱٪ سرمایه در هر معامله، «مجموع ۱۰R» "
    "یعنی حدود ۱۰٪ سود و «بیشترین افت ۵R» یعنی در بدترین دوره حدود ۵٪ افت."
)

st.subheader("🎯 کدام استراتژی به هدف نزدیک‌تر است؟")
st.caption(
    "هر استراتژی روی یک حساب واقعی با ریسک ۰٫۵٪ در هر معامله، سقف ضرر روزانه‌ی ۱٫۵٪ "
    "و حداکثر ۳ پوزیشن باز، جدا برای ارزهای پرحجم. «ریسک لازم برای ۱۰٪» یعنی با "
    "همین تعداد و کیفیت سیگنال، ریسک هر معامله باید چقدر باشد تا ماهی ۱۰٪ دربیاید."
)
_ranks = {symbol: k + 1 for k, symbol in enumerate(report["symbols"])}
_goal_rows = []
for _label, _trades in report["results"]:
    for _name, _limit in (("۳۰ پرحجم", 30), ("۱۰۰ پرحجم", 100), ("۲۰۰ پرحجم", 200), ("همه", 10**9)):
        if _limit < 10**9 and _limit >= len(report["symbols"]) and _name != "۳۰ پرحجم":
            continue
        _subset = [t for t in _trades if _ranks.get(t["symbol"], 10**9) <= _limit]
        if not _subset:
            continue
        _acc = simulate_account(_subset, 0.5, 1.5, 3)
        _r_month = sum(t["r"] for t in _subset) / (report["settings"]["days"] / 30)
        _goal_rows.append({
            "استراتژی": _label,
            "ارزها": _name,
            "معامله در ماه": round(len(_subset) / (report["settings"]["days"] / 30), 1),
            "R در ماه": round(_r_month, 2),
            "سود ماهانه‌ی حساب (٪)": _acc["avg_month_percent"],
            "ماه‌های ≥۱۰٪": str(_acc["months_at_least_10"]) + "/" + str(_acc["full_months"]),
            "بیشترین افت (٪)": _acc["max_drawdown_percent"],
            "ریسک لازم برای ۱۰٪": (format(10 / _r_month, ".1f") + "٪") if _r_month > 0 else "—",
        })
_goal_rows.sort(key=lambda row: row["سود ماهانه‌ی حساب (٪)"], reverse=True)
st.table(_goal_rows[:15])


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

VOLUME_TIERS = [
    ("۳۰ ارز پرحجم اول", 1, 30),
    ("رتبه‌ی ۳۱ تا ۱۰۰", 31, 100),
    ("رتبه‌ی ۱۰۱ تا ۲۰۰", 101, 200),
    ("رتبه‌ی ۲۰۱ به بعد (کم‌حجم)", 201, 10**9),
]
# report["symbols"] به ترتیب حجم ۲۴ ساعته (پرحجم اول) است
ranks = {symbol: k + 1 for k, symbol in enumerate(report["symbols"])}
all_chosen = dict(report["results"])[chosen]

if ranks:
    st.markdown("**نتیجه‌ی همین استراتژی به تفکیک حجم معاملات ارز** (رتبه بر اساس حجم ۲۴ ساعته‌ی امروز)")
    tier_rows = []
    for name, low, high in VOLUME_TIERS:
        tier = summarize([t for t in all_chosen if low <= ranks.get(t["symbol"], 10**9) <= high])
        if tier["trades"]:
            tier_rows.append({
                "گروه": name, "معاملات": tier["trades"], "نرخ برد (٪)": tier["win_rate"],
                "مجموع (R)": tier["total_r"], "Profit factor": tier["profit_factor"],
            })
    st.dataframe(tier_rows, use_container_width=True, hide_index=True)

    universe = st.selectbox(
        "حساب را فقط با این ارزها حساب کن",
        ["همه‌ی ارزها", "۳۰ پرحجم", "۱۰۰ پرحجم", "۲۰۰ پرحجم"],
    )
    limit_rank = {"همه‌ی ارزها": 10**9, "۳۰ پرحجم": 30, "۱۰۰ پرحجم": 100, "۲۰۰ پرحجم": 200}[universe]
    chosen_trades = [t for t in all_chosen if ranks.get(t["symbol"], 10**9) <= limit_rank]
else:
    chosen_trades = all_chosen

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
