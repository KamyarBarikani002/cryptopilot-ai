import os
from unittest import mock

import pytest

from src import remember_me
from src.password_utils import hash_password

KEY = hash_password("p", "s")

STUB_PAGE = "tests/login_stub_page.py"


# ---------------- token ----------------

def test_token_round_trip_and_expiry():
    token = remember_me.make_token(KEY, now=1_000_000, days=30)
    assert remember_me.token_is_valid(token, KEY, now=1_000_000 + 29 * 86400)
    assert not remember_me.token_is_valid(token, KEY, now=1_000_000 + 30 * 86400)


@pytest.mark.parametrize("bad", [None, "", "abc", "123", "123.", ".abc", "12a.ff", 5])
def test_garbage_tokens_are_rejected(bad):
    assert not remember_me.token_is_valid(bad, KEY, now=0)


def test_tampered_or_foreign_tokens_are_rejected():
    token = remember_me.make_token(KEY, now=1_000_000)
    expires, sig = token.split(".")
    longer = str(int(expires) + 10**9) + "." + sig
    assert not remember_me.token_is_valid(longer, KEY, now=1_000_000)
    # changing the panel password must log every remembered browser out
    assert not remember_me.token_is_valid(token, hash_password("new", "s"), now=1_000_000)


def test_cookie_script_sets_and_clears():
    set_js = remember_me._cookie_script("123.abc", 3600)
    assert "cryptopilot_session=123.abc; Max-Age=3600; Path=/; SameSite=Strict" in set_js
    assert "Max-Age=0" in remember_me._cookie_script("", 0)


# ---------------- the login screen ----------------

def _app(cookie=None):
    from streamlit.testing.v1 import AppTest
    os.environ["APP_PASSWORD_SALT"] = "s"
    os.environ["APP_PASSWORD_HASH"] = KEY
    # on Streamlit Cloud the request carries no cookies, so the browser-side
    # reader is what actually finds the token: test through that path
    patcher = mock.patch.multiple(
        "src.remember_me", read_cookie=mock.DEFAULT, read_cookie_via_browser=mock.DEFAULT
    )
    mocks = patcher.start()
    mocks["read_cookie"].return_value = None
    mocks["read_cookie_via_browser"].return_value = cookie
    return AppTest.from_file(STUB_PAGE), patcher


def _shows_panel(at):
    return any("PANEL CONTENT" in m.value for m in at.markdown)


def test_login_with_remember_me_writes_the_cookie():
    at, patcher = _app()
    try:
        at.run()
        assert not _shows_panel(at)
        assert at.checkbox[0].value is True, "remember me is on by default"
        at.text_input[0].input("p")
        at.button[0].click().run()
        assert not at.exception
        assert _shows_panel(at)
        assert "pending_cookie" not in at.session_state, "cookie must be written once, then forgotten"
    finally:
        patcher.stop()


def test_login_without_remember_me_does_not_write_a_cookie():
    at, patcher = _app()
    try:
        at.run()
        at.text_input[0].input("p")
        at.checkbox[0].uncheck()
        with mock.patch("src.remember_me.write_cookie") as write:
            at.button[0].click().run()
        assert _shows_panel(at)
        write.assert_not_called()
    finally:
        patcher.stop()


def test_wrong_password_never_gets_in():
    at, patcher = _app()
    try:
        at.run()
        at.text_input[0].input("wrong")
        at.button[0].click().run()
        assert not _shows_panel(at)
        assert any("اشتباه" in e.value for e in at.error)
    finally:
        patcher.stop()


def test_valid_cookie_skips_the_password_and_logout_ignores_it():
    at, patcher = _app(cookie=remember_me.make_token(KEY))
    try:
        at.run()
        assert not at.exception
        assert _shows_panel(at), "a remembered browser goes straight in"
        logout = [b for b in at.button if b.label == "🚪 خروج"][0]
        logout.click().run()
        assert not _shows_panel(at), "logout must not be undone by the old cookie"
        assert at.text_input[0].label == "رمز عبور"
    finally:
        patcher.stop()


def test_expired_or_forged_cookie_still_asks_for_the_password():
    at, patcher = _app(cookie=remember_me.make_token(KEY, now=0))
    try:
        at.run()
        assert not _shows_panel(at)
    finally:
        patcher.stop()
    at, patcher = _app(cookie=remember_me.make_token(hash_password("other", "s")))
    try:
        at.run()
        assert not _shows_panel(at)
    finally:
        patcher.stop()
