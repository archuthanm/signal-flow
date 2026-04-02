from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from market_monitor.app.config import DEDUPLICATION_LOOKBACK_HOURS
from market_monitor.app.models import Article, ArticlePayload
from market_monitor.app.utils.text import jaccard_similarity, normalise_title


class DuplicateDetector:
    def __init__(self, similarity_threshold: float = 0.8) -> None:
        self.similarity_threshold = similarity_threshold

    def check(self, session: Session, article: ArticlePayload) -> tuple[bool, str | None]:
        existing_url = session.scalar(select(Article.id).where(Article.url == article.url))
        if existing_url is not None:
            return True, "duplicate_url"

        normalised_title = normalise_title(article.title)
        recent_candidates = self._recent_candidates_query(article.published_at)
        for candidate in session.scalars(recent_candidates):
            if candidate.is_duplicate:
                continue
            if normalise_title(candidate.title) == normalised_title:
                return True, "duplicate_title"
            if candidate.source == article.source:
                similarity = jaccard_similarity(candidate.title, article.title)
                if similarity >= self.similarity_threshold:
                    return True, "near_duplicate_title"

        return False, None

    def _recent_candidates_query(self, published_at: datetime | None) -> Select[tuple[Article]]:
        baseline = published_at or datetime.now(UTC).replace(tzinfo=None)
        window_start = baseline - timedelta(hours=DEDUPLICATION_LOOKBACK_HOURS)
        return select(Article).where(Article.created_at >= window_start)
