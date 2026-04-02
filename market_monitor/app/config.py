from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

BASE_DIR: Final[Path] = Path(__file__).resolve().parents[2]
DATA_DIR: Final[Path] = BASE_DIR / "data"
OUTPUT_DIR: Final[Path] = BASE_DIR / "output"
TEMPLATE_DIR: Final[Path] = Path(__file__).resolve().parent / "templates"

load_dotenv(BASE_DIR / ".env")


def google_news_rss_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search?"
        f"q={query.replace(' ', '+')}&hl=en-GB&gl=GB&ceid=GB:en"
    )

APP_NAME: Final[str] = os.getenv("MARKET_MONITOR_APP_NAME", "Market Monitor")
TIMEZONE: Final[str] = os.getenv("MARKET_MONITOR_TIMEZONE", "Europe/London")
DATABASE_URL: Final[str] = os.getenv(
    "MARKET_MONITOR_DATABASE_URL",
    f"sqlite:///{(DATA_DIR / 'market_monitor.db').as_posix()}",
)
OUTPUT_FILE_TEMPLATE: Final[str] = os.getenv(
    "MARKET_MONITOR_OUTPUT_FILE_TEMPLATE",
    "daily_digest_{date}.md",
)
TOP_ARTICLES_PER_SECTOR: Final[int] = int(
    os.getenv("MARKET_MONITOR_TOP_ARTICLES_PER_SECTOR", "5")
)
MAX_SUMMARY_SENTENCES: Final[int] = int(
    os.getenv("MARKET_MONITOR_MAX_SUMMARY_SENTENCES", "2")
)
MIN_RELEVANCE_FOR_DIGEST: Final[int] = int(
    os.getenv("MARKET_MONITOR_MIN_RELEVANCE_FOR_DIGEST", "6")
)
MAX_ARTICLES_TO_SUMMARISE: Final[int] = int(
    os.getenv("MARKET_MONITOR_MAX_ARTICLES_TO_SUMMARISE", "18")
)
DEDUPLICATION_LOOKBACK_HOURS: Final[int] = int(
    os.getenv("MARKET_MONITOR_DEDUPLICATION_LOOKBACK_HOURS", "48")
)
MAX_ARTICLE_AGE_DAYS: Final[int] = int(
    os.getenv("MARKET_MONITOR_MAX_ARTICLE_AGE_DAYS", "7")
)

TRUSTED_SOURCE_BONUS: Final[dict[str, int]] = {
    "Reuters": 2,
    "Bloomberg": 2,
    "Financial Times": 2,
    "Wall Street Journal": 2,
    "WSJ": 2,
}

RSS_FEEDS: Final[dict[str, str]] = {
    "Professional Macro / Rates": google_news_rss_url(
        '(Reuters OR Bloomberg OR "Financial Times" OR WSJ) '
        '(Fed OR "Federal Reserve" OR ECB OR "Bank of England" OR inflation OR "interest rates" OR "bond yields")'
    ),
    "Professional Banking": google_news_rss_url(
        '(Reuters OR Bloomberg OR "Financial Times" OR WSJ) '
        '(JPMorgan OR Goldman Sachs OR Morgan Stanley OR HSBC OR Wells Fargo OR banking OR lender OR "stress test")'
    ),
    "Professional Fintech": google_news_rss_url(
        '(Reuters OR Bloomberg OR "Financial Times" OR WSJ) '
        '(fintech OR Stripe OR PayPal OR Block OR Plaid OR "digital payments" OR "open banking")'
    ),
    "Professional Markets": google_news_rss_url(
        '(Reuters OR Bloomberg OR "Financial Times" OR WSJ) '
        '(markets OR trading OR yields OR earnings OR regulation OR merger)'
    ),
    "Professional Earnings": google_news_rss_url(
        '(Reuters OR Bloomberg OR "Financial Times" OR WSJ) '
        '(earnings OR guidance OR results OR forecast OR revenue) '
        '(bank OR fintech OR payments OR lender)'
    ),
    "Professional Regulation": google_news_rss_url(
        '(Reuters OR Bloomberg OR "Financial Times" OR WSJ) '
        '(regulation OR regulatory OR antitrust OR sanctions OR lawsuit OR "stress test") '
        '(banking OR fintech OR payments OR markets)'
    ),
}

ALLOWED_SOURCE_PATTERNS: Final[tuple[str, ...]] = (
    "reuters",
    "financial times",
    "ft",
    "wsj",
    "wall street journal",
    "bloomberg",
)

LOW_SIGNAL_TITLE_PATTERNS: Final[tuple[str, ...]] = (
    "best ",
    "how to ",
    "top ",
    "stocks to buy",
    "long-term bet",
    "compelling",
    "resilient path",
    "unlocking",
    "redefining",
    "future of",
    "offer a resilient path",
)

SECTOR_KEYWORDS: Final[dict[str, list[str]]] = {
    "macro_rates": [
        "bank of england",
        "bond market",
        "bond yield",
        "central bank",
        "consumer price index",
        "ecb",
        "fed",
        "federal reserve",
        "gilts",
        "inflation",
        "interest rate",
        "monetary policy",
        "rate cut",
        "rate hike",
        "treasury yield",
        "yield curve",
    ],
    "banking": [
        "bank",
        "banking",
        "capital ratio",
        "credit loss",
        "deposits",
        "goldman sachs",
        "hsbc",
        "jpmorgan",
        "loan losses",
        "morgan stanley",
        "net interest income",
        "wells fargo",
    ],
    "fintech": [
        "block",
        "digital payments",
        "embedded finance",
        "fintech",
        "mobile wallet",
        "neobank",
        "open banking",
        "payment processor",
        "paypal",
        "plaid",
        "square",
        "stripe",
    ],
}

COMMON_FINANCE_TERMS: Final[list[str]] = [
    "acquisition",
    "assets",
    "balance sheet",
    "capital",
    "credit",
    "earnings",
    "funding",
    "ipo",
    "liquidity",
    "markets",
    "merger",
    "regulation",
    "revenue",
    "trading",
]

MARKET_MOVING_TERMS: Final[list[str]] = [
    "acquisition",
    "antitrust",
    "bond yields",
    "capital raise",
    "central bank",
    "cuts outlook",
    "cuts rates",
    "earnings",
    "forecast",
    "funding round",
    "guidance",
    "inflation",
    "interest rates",
    "ipo",
    "lawsuit",
    "merger",
    "misses expectations",
    "monetary policy",
    "raises rates",
    "rate cut",
    "rate hike",
    "regulation",
    "regulatory",
    "restructuring",
    "results",
    "revenue",
    "shares fall",
    "shares rise",
    "sanctions",
    "stress test",
    "surge",
    "warning",
]

MAJOR_MARKET_ENTITIES: Final[list[str]] = [
    "bank of england",
    "block",
    "ecb",
    "federal reserve",
    "fed",
    "goldman sachs",
    "hsbc",
    "jpmorgan",
    "mastercard",
    "morgan stanley",
    "paypal",
    "plaid",
    "sofi",
    "stripe",
    "visa",
    "wells fargo",
]

STOPWORDS: Final[set[str]] = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}

SECTOR_DISPLAY_NAMES: Final[dict[str, str]] = {
    "macro_rates": "Macro / Rates",
    "banking": "Banking / Financial Institutions",
    "fintech": "Fintech",
}

EXCLUDED_TERMS: Final[list[str]] = [
    "cryptocurrency",
    "crypto",
    "retail investor",
    "personal finance",
]

def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
