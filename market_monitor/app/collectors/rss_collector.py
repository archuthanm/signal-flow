from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import feedparser
import requests

from market_monitor.app.config import (
    ALLOWED_SOURCE_PATTERNS,
    LOW_SIGNAL_TITLE_PATTERNS,
    MAX_ARTICLE_AGE_DAYS,
    RSS_FEEDS,
)
from market_monitor.app.models import ArticlePayload
from market_monitor.app.utils.text import (
    canonicalise_url,
    clean_whitespace,
    normalise_text,
    parse_datetime,
    strip_html,
)

LOGGER = logging.getLogger(__name__)


class RSSCollector:
    def __init__(self, feeds: dict[str, str] | None = None, timeout: int = 20) -> None:
        self.feeds = feeds or RSS_FEEDS
        self.timeout = timeout

    def collect(self) -> list[ArticlePayload]:
        articles: list[ArticlePayload] = []
        for source_name, feed_url in self.feeds.items():
            try:
                response = requests.get(
                    feed_url,
                    headers={"User-Agent": "market-monitor/1.0"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                LOGGER.warning("Failed to fetch feed %s: %s", source_name, exc)
                continue

            parsed = feedparser.parse(response.content)
            for entry in parsed.entries:
                article = self._to_article_payload(source_name, entry)
                if article:
                    articles.append(article)

        LOGGER.info("Collected %s raw articles from %s feeds", len(articles), len(self.feeds))
        return articles

    def _to_article_payload(self, source_name: str, entry: feedparser.FeedParserDict) -> ArticlePayload | None:
        title = clean_whitespace(entry.get("title"))
        url = entry.get("link")
        if not title or not url:
            return None

        description = strip_html(entry.get("summary") or entry.get("description"))
        content_parts = entry.get("content") or []
        content = " ".join(strip_html(part.get("value")) for part in content_parts if part.get("value"))
        source = clean_whitespace(entry.get("source", {}).get("title")) or self._extract_source_from_title(title)
        published_at = parse_datetime(entry.get("published") or entry.get("updated"))
        if not self._is_allowed_source(source_name, source):
            return None
        if self._is_low_signal_title(title):
            return None
        if self._is_stale(published_at):
            return None

        return ArticlePayload(
            title=self._strip_source_suffix(title, source),
            source=source,
            url=canonicalise_url(url),
            published_at=published_at,
            description=description or None,
            content=content or None,
        )

    def _is_allowed_source(self, source_name: str, source: str) -> bool:
        source_text = normalise_text(f"{source_name} {source}")
        return any(pattern in source_text for pattern in ALLOWED_SOURCE_PATTERNS)

    def _is_low_signal_title(self, title: str) -> bool:
        normalised_title = normalise_text(title)
        return any(pattern in normalised_title for pattern in LOW_SIGNAL_TITLE_PATTERNS)

    def _is_stale(self, published_at: datetime | None) -> bool:
        if published_at is None:
            return False
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=MAX_ARTICLE_AGE_DAYS)
        return published_at < cutoff

    def _extract_source_from_title(self, title: str) -> str:
        if " - " not in title:
            return ""
        return clean_whitespace(title.rsplit(" - ", 1)[-1])

    def _strip_source_suffix(self, title: str, source: str) -> str:
        if not source:
            return title
        suffix = f" - {source}"
        if title.endswith(suffix):
            return title[: -len(suffix)].strip()
        return title
