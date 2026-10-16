"""
«مرا به خاطر بسپار» برای ورود به پنل.

بعد از ورود موفق، یک توکن امضاشده در کوکی مرورگر گذاشته می‌شود تا با رفرش یا
بستن و باز کردن تب دوباره رمز نخواهد.

- توکن = «زمان انقضا» + امضای HMAC آن با هش رمز پنل. پس خود رمز هیچ‌جا ذخیره
  نمی‌شود، و اگر رمز پنل عوض شود همه‌ی توکن‌های قبلی خودبه‌خود باطل می‌شوند.
- نوشتن و پاک کردن کوکی با یک اسکریپت کوچک در یک iframe نامرئی انجام می‌شود.
  خواندن اول از st.context.cookies و اگر نبود (Streamlit Cloud) با کامپوننت
  نامرئی src/cookie_reader که کوکی را از خود مرورگر می‌خواند.
"""

import hashlib
import hmac
import os
import time

COOKIE_NAME = "cryptopilot_session"
REMEMBER_DAYS = 30

_SIGNING_LABEL = "cryptopilot-remember-me:"


def _signature(expires_at: int, signing_key: str) -> str:

    return hmac.new(
        signing_key.encode(),
        (_SIGNING_LABEL + str(expires_at)).encode(),
        hashlib.sha256,
    ).hexdigest()


def make_token(signing_key: str, now: float | None = None, days: int = REMEMBER_DAYS) -> str:

    now = time.time() if now is None else now
    expires_at = int(now) + days * 24 * 3600

    return str(expires_at) + "." + _signature(expires_at, signing_key)


def token_is_valid(token, signing_key: str, now: float | None = None) -> bool:

    if not token or not signing_key or not isinstance(token, str):
        return False

    expires_part, _, signature = token.partition(".")

    if not expires_part.isdigit() or not signature:
        return False

    expires_at = int(expires_part)
    now = time.time() if now is None else now

    if expires_at <= now:
        return False

    return hmac.compare_digest(signature, _signature(expires_at, signing_key))


def read_cookie():

    """
    کوکی از هدرهای اولین درخواست همین نشست (st.context.cookies)، یا None.
    روی اجرای لوکال کار می‌کند؛ روی Streamlit Community Cloud پروکسی کوکی‌ها را
    حذف می‌کند، برای همین read_cookie_via_browser هم هست.
    """

    try:
        import streamlit as st
        return st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None


_reader = None


def read_cookie_via_browser():

    """
    کوکی را مستقیم از خود مرورگر می‌خواند (کامپوننت نامرئی src/cookie_reader).
    بار اول None برمی‌گرداند و وقتی مرورگر جواب داد، صفحه خودش دوباره اجرا
    می‌شود و مقدار (یا "" اگر کوکی نبود) برمی‌گردد.
    """

    global _reader

    try:
        import streamlit.components.v1 as components

        if _reader is None:
            _reader = components.declare_component(
                "cookie_reader",
                path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie_reader"),
            )

        return _reader(name=COOKIE_NAME, key="cryptopilot_cookie_reader", default=None)
    except Exception:
        return None


def _cookie_script(value: str, max_age_seconds: int) -> str:

    # value فقط رقم، نقطه و هگز است (یا خالی)، پس نیازی به escape ندارد
    return (
        "<script>"
        "try {"
        "  var secure = window.parent.location.protocol === 'https:' ? '; Secure' : '';"
        "  window.parent.document.cookie = '" + COOKIE_NAME + "=" + value
        + "; Max-Age=" + str(max_age_seconds) + "; Path=/; SameSite=Strict' + secure;"
        "} catch (e) { console.log('[CryptoPilot] cookie: ' + e); }"
        "</script>"
    )


def write_cookie(token: str, days: int = REMEMBER_DAYS):

    import streamlit.components.v1 as components
    components.html(_cookie_script(token, days * 24 * 3600), height=0)


def clear_cookie():

    import streamlit.components.v1 as components
    components.html(_cookie_script("", 0), height=0)
