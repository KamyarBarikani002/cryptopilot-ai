"""
تحلیل ساده‌ی احساسات خبر (کلمات کلیدی) و تشخیص اینکه خبر درباره‌ی کدام ارز است.

این یک مدل زبانی نیست؛ فقط کلمات پرتکرار خبرهای کریپتو را وزن می‌دهد (مثلاً
hack/exploit/delist منفی قوی، ETF approval/listing/partnership مثبت). هدف فقط
این است که خبرهای خیلی منفی یا خیلی مثبت یک ارز، جلوی سیگنال خلاف‌جهت را بگیرند.
"""

import re

# (الگو، وزن). الگوها کلمه‌ی کامل‌اند (\b)، تا مثلاً delist با list قاطی نشود.
_LEXICON = [
    # منفی قوی
    (r"hack(?:ed|s|er|ers)?", -3), (r"exploit(?:ed|s)?", -3), (r"drain(?:ed|s)?", -3),
    (r"rug ?pull(?:ed|s)?", -3), (r"delist(?:ed|s|ing)?", -3), (r"bankrupt(?:cy)?", -3),
    (r"insolven(?:t|cy)", -3), (r"fraud(?:ulent)?", -3), (r"ponzi", -3), (r"scam(?:s|mer|mers)?", -3),
    # منفی
    (r"lawsuit(?:s)?", -2), (r"sue(?:s|d)", -2), (r"charge[sd]", -2), (r"arrest(?:ed|s)?", -2),
    (r"ban(?:s|ned)?", -2), (r"halt(?:s|ed)?", -2), (r"suspend(?:s|ed)?", -2), (r"crash(?:es|ed)?", -2),
    (r"plunge(?:s|d)?", -2), (r"tumble(?:s|d)?", -2), (r"vulnerabilit(?:y|ies)", -2),
    (r"attack(?:s|ed)?", -2), (r"breach(?:es|ed)?", -2), (r"outflows?", -1), (r"outage(?:s)?", -1),
    (r"liquidat(?:ion|ions|ed)", -1), (r"sell-?off(?:s)?", -1), (r"dump(?:s|ed)?", -1),
    (r"investigat(?:ion|es|ed)", -1), (r"downgrade(?:s|d)?", -1), (r"bearish", -1), (r"slump(?:s|ed)?", -1),
    # مثبت قوی
    (r"etf approv(?:al|ed|es)", 3), (r"approv(?:al|ed|es) (?:of )?(?:a |the )?(?:spot )?etf", 3),
    # مثبت
    (r"list(?:s|ed|ing)", 2), (r"partnership(?:s)?", 2), (r"mainnet", 2), (r"adoption", 2),
    (r"surge(?:s|d)?", 2), (r"rall(?:y|ies|ied)", 2), (r"soar(?:s|ed)?", 2), (r"inflows?", 2),
    (r"all-time high", 2), (r"record high", 2), (r"buyback(?:s)?", 2), (r"approv(?:al|ed|es)", 1),
    (r"partner(?:s|ed)?", 1), (r"integrat(?:ion|es|ed)", 1), (r"launch(?:es|ed)?", 1),
    (r"upgrade(?:s|d)?", 1), (r"bullish", 1), (r"acqui(?:re|res|red|sition)", 1), (r"burn(?:s|ed)?", 1),
    (r"jump(?:s|ed)?", 1), (r"gain(?:s|ed)?", 1),
]

_COMPILED = [(re.compile(r"\b" + pattern + r"\b", re.IGNORECASE), weight) for pattern, weight in _LEXICON]

# delist شامل list هم هست؛ وقتی delist پیدا شد، list را حساب نمی‌کنیم
_DELIST = re.compile(r"\bdelist", re.IGNORECASE)
_LIST = re.compile(r"\blist(?:s|ed|ing)\b", re.IGNORECASE)


def sentiment_score(text):

    if not text:
        return 0

    score = 0
    for pattern, weight in _COMPILED:
        if pattern.pattern.startswith(r"\blist") and _DELIST.search(text):
            continue
        if pattern.search(text):
            score += weight

    return max(-6, min(6, score))


# نام کامل ارزهای مهم؛ بقیه فقط با نماد (با حروف بزرگ) پیدا می‌شوند
COIN_NAMES = {
    "BTC": ["bitcoin"], "ETH": ["ethereum", "ether"], "SOL": ["solana"], "XRP": ["ripple", "xrp"],
    "DOGE": ["dogecoin"], "ADA": ["cardano"], "BNB": ["bnb", "binance coin"], "TON": ["toncoin"],
    "TRX": ["tron"], "AVAX": ["avalanche"], "LINK": ["chainlink"], "DOT": ["polkadot"],
    "POL": ["polygon"], "SHIB": ["shiba inu"], "LTC": ["litecoin"], "BCH": ["bitcoin cash"],
    "NEAR": ["near protocol"], "UNI": ["uniswap"], "APT": ["aptos"], "ARB": ["arbitrum"],
    "OP": ["optimism"], "SUI": ["sui"], "SEI": ["sei"], "INJ": ["injective"], "TIA": ["celestia"],
    "PEPE": ["pepe"], "WIF": ["dogwifhat"], "ATOM": ["cosmos"], "FIL": ["filecoin"],
    "ETC": ["ethereum classic"], "HBAR": ["hedera"], "ICP": ["internet computer"], "XLM": ["stellar"],
    "AAVE": ["aave"], "ONDO": ["ondo"], "ENA": ["ethena"], "TAO": ["bittensor"], "RENDER": ["render"],
    "FET": ["fetch.ai"], "WLD": ["worldcoin"], "JUP": ["jupiter"], "HYPE": ["hyperliquid"],
    "ZEC": ["zcash"], "LDO": ["lido"], "CRV": ["curve finance"], "KCS": ["kucoin token"],
}

# نمادهایی که کلمه‌ی معمولی انگلیسی یا اصطلاح عمومی‌اند
_AMBIGUOUS = {
    "THE", "FOR", "AND", "ONE", "ALL", "NOW", "NEW", "CEO", "ETF", "SEC", "USD", "USA", "FED", "CPI",
    "GDP", "NFT", "DAO", "API", "ATH", "TVL", "APR", "APY", "IPO", "OTC", "DEX", "CEX", "WEB", "NET",
    "HOT", "BIG", "KEY", "TOP", "WIN", "RUN", "SUN", "GAS", "MOVE", "OPEN", "REAL", "SAFE", "LOW",
    "HIGH", "BOND", "GOLD", "DATA", "MEME", "COIN", "CAT", "DOG", "AI", "OK", "US", "UK", "EU",
}

_ALIASES = {"XBT": "BTC"}


def normalize_coin(base):
    base = (base or "").upper()
    return _ALIASES.get(base, base)


def mentioned_coins(text, include_short=False):

    """نمادهای ارزهایی که در متن آمده‌اند: با نام کامل یا با نماد (مثل $SOL یا SOL)."""

    found = set()

    if not text:
        return found

    lowered = text.lower()

    for symbol, names in COIN_NAMES.items():
        for name in names:
            if re.search(r"\b" + re.escape(name) + r"\b", lowered):
                found.add(symbol)
                break

    for token in re.findall(r"\$?\b[A-Z0-9]{2,10}\b", text):
        symbol = token.lstrip("$")
        if symbol in _AMBIGUOUS or symbol.isdigit():
            continue
        if len(symbol) < 3 and not (include_short or token.startswith("$")):
            continue
        found.add(normalize_coin(symbol))

    return found
