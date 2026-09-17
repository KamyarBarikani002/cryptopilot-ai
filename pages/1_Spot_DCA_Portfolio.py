import contextlib
import io

import streamlit as st

from src.auth import require_login

require_login()

from config.settings import ASSET_SYMBOLS, PROJECT_NAME  # noqa: E402
from src.market_data import get_prices  # noqa: E402
from src.portfolio.portfolio_state import load_state  # noqa: E402
from src.core.pipeline import CryptoPilotPipeline  # noqa: E402


st.set_page_config(
    page_title=PROJECT_NAME + " - پرتفوی DCA",
    page_icon="💰",
    layout="wide"
)

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

st.title("💰 " + PROJECT_NAME + " — پرتفوی DCA/سرمایه‌گذاری ماهانه")

st.caption(
    "این بخش هر ماه یک مبلغ ثابت رو بر اساس رژیم فعلی بازار (صعودی/نزولی/"
    "انباشت) بین چند ارز تخصیص می‌ده و پوزیشن BTC رو طبق تحلیل تکنیکال "
    "مدیریت می‌کنه. جدا از اسکنر فیوچرز است؛ این یک استراتژی بلندمدت‌تر و "
    "محافظه‌کارانه‌تره."
)

state = load_state()

try:
    prices = get_prices(ASSET_SYMBOLS)
    price_error = None
except Exception as error:
    prices = {}
    price_error = str(error)

if price_error:
    st.warning(
        "اتصال به بایننس برای گرفتن قیمت لحظه‌ای دارایی‌ها برقرار نشد: " +
        price_error + " — مقادیر زیر با آخرین قیمت ذخیره‌شده نیست."
    )

portfolio_value = state["cash"]
breakdown = {"نقد (Cash)": round(state["cash"], 2)}

for asset, units in state["holdings"].items():
    price = prices.get(asset, 0)
    asset_value = units * price
    portfolio_value += asset_value
    breakdown[asset] = round(asset_value, 2)

pnl = round(portfolio_value - state["total_contributed"], 2)

col1, col2, col3 = st.columns(3)
col1.metric("ارزش کل پرتفوی", "$" + str(round(portfolio_value, 2)))
col2.metric("کل سرمایه واریزشده", "$" + str(round(state["total_contributed"], 2)))
col3.metric("سود/زیان کلی", "$" + str(pnl), delta=str(pnl))

st.subheader("ترکیب دارایی‌ها")

st.dataframe(
    [{"دارایی": name, "ارزش ($)": value} for name, value in breakdown.items()],
    width='stretch',
    hide_index=True
)

st.divider()

st.subheader("اجرای یک چرخه تحلیل/تصمیم‌گیری")

st.caption(
    "این دکمه یک چرخه کامل رو اجرا می‌کند: گرفتن قیمت لحظه‌ای، تحلیل "
    "تکنیکال، تشخیص رژیم بازار، تصمیم خرید/فروش/نگه‌داری BTC، مدیریت ریسک، و "
    "اگر ماه جدیدی شروع شده باشد، واریز و تخصیص ماهانه را هم انجام می‌دهد. "
    "همه این تغییرات مستقیم روی پرتفوی واقعی (ذخیره‌شده در دیتابیس) اعمال "
    "می‌شود."
)

if st.button("▶️ اجرای یک چرخه", type="primary"):

    output_buffer = io.StringIO()

    try:
        with contextlib.redirect_stdout(output_buffer):
            engine = CryptoPilotPipeline()
            engine.run()
        st.success("اجرا با موفقیت انجام شد.")
    except Exception as error:
        st.error("خطا در اجرای چرخه: " + str(error))

    with st.expander("خروجی کامل اجرا", expanded=True):
        st.code(output_buffer.getvalue() or "(خروجی‌ای ثبت نشد)")

    st.rerun()

if state["contributions"]:

    st.divider()
    st.subheader("تاریخچه واریزهای ماهانه")

    st.dataframe(
        [
            {
                "دوره": c["period"],
                "مبلغ ($)": c["amount"],
                "رژیم بازار": c["regime"],
                "زمان": c["time"]
            }
            for c in reversed(state["contributions"])
        ],
        width='stretch',
        hide_index=True
    )
