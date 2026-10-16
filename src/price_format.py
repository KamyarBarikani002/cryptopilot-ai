"""
قیمت ارزهای خیلی ارزان (مثل PEPE با قیمت 0.0000040879) با ۶ رقم اعشار صفر
یا بی‌معنی می‌شد. اینجا دو کار انجام می‌شود:

- round_to_tick: گرد کردن قیمت به گام قیمت (tickSize) همان قرارداد در کوکوین،
  تا حد ضرر/حد سود عددی باشد که واقعاً در صرافی قابل ثبت است.
- format_price: نمایش تا ۱۰ رقم اعشار، بدون صفرهای اضافه‌ی آخر.
"""

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal

PRICE_DECIMALS = 10

_ROUNDING = {"nearest": ROUND_HALF_UP, "down": ROUND_FLOOR, "up": ROUND_CEILING}


def round_to_tick(price, tick_size=None, mode="nearest"):

    """
    price را به نزدیک‌ترین مضرب tick_size گرد می‌کند (یا رو به پایین/بالا).
    اگر tick_size معلوم نباشد، به ۱۰ رقم اعشار گرد می‌شود.
    """

    if price is None:
        return None

    tick = Decimal(str(tick_size)) if tick_size else Decimal(1).scaleb(-PRICE_DECIMALS)

    if tick <= 0:
        tick = Decimal(1).scaleb(-PRICE_DECIMALS)

    steps = (Decimal(str(price)) / tick).quantize(Decimal(1), rounding=_ROUNDING[mode])

    return float(steps * tick)


def format_price(price, decimals=PRICE_DECIMALS):

    """82072.9 -> '82,072.9' ، 0.0000040879 -> '0.0000040879' ، None -> '—'"""

    if price is None:
        return "—"

    try:
        value = float(price)
    except (TypeError, ValueError):
        return str(price)

    text = format(Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP), ",f")

    if "." in text:
        text = text.rstrip("0").rstrip(".")

    return "0" if text in ("-0", "") else text
