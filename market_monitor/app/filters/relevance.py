from __future__ import annotations

from dataclasses import dataclass

from market_monitor.app.config import (
    COMMON_FINANCE_TERMS,
    EXCLUDED_TERMS,
    MAJOR_MARKET_ENTITIES,
    MARKET_MOVING_TERMS,
    SECTOR_KEYWORDS,
    TRUSTED_SOURCE_BONUS,
)
from market_monitor.app.models import ArticlePayload
from market_monitor.app.utils.text import normalise_text


@dataclass(slots=True)
class RelevanceResult:
    sector: str | None
    score: float
    matched_keywords: list[str]


class RelevanceScorer:
    def __init__(self, sector_keywords: dict[str, list[str]] | None = None) -> None:
        self.sector_keywords = sector_keywords or SECTOR_KEYWORDS

    def score(self, article: ArticlePayload) -> RelevanceResult:
        title = normalise_text(article.title)
        description = normalise_text(article.description)
        content = normalise_text(article.content)
        combined = " ".join(part for part in [title, description, content] if part)

        if any(term in combined for term in EXCLUDED_TERMS):
            return RelevanceResult(sector=None, score=0.0, matched_keywords=[])

        sector_scores: dict[str, float] = {}
        matched_keywords: dict[str, list[str]] = {}

        for sector, keywords in self.sector_keywords.items():
            score = 0.0
            sector_matches: list[str] = []
            for keyword in keywords:
                needle = keyword.lower()
                if needle in title:
                    score += 3
                    sector_matches.append(keyword)
                elif needle in description:
                    score += 2
                    sector_matches.append(keyword)
                elif needle in content:
                    score += 1
                    sector_matches.append(keyword)
            if score:
                sector_scores[sector] = score
                matched_keywords[sector] = sector_matches

        finance_term_hits = sum(1 for term in COMMON_FINANCE_TERMS if term in combined)
        if finance_term_hits >= 2:
            for sector in sector_scores:
                sector_scores[sector] += 1

        market_moving_hits = sum(1 for term in MARKET_MOVING_TERMS if term in combined)
        major_entity_hits = sum(1 for term in MAJOR_MARKET_ENTITIES if term in combined)
        title_market_hits = sum(1 for term in MARKET_MOVING_TERMS if term in title)
        title_entity_hits = sum(1 for term in MAJOR_MARKET_ENTITIES if term in title)

        has_investor_signal = (
            title_market_hits >= 1
            or title_entity_hits >= 1
            or (title_market_hits >= 1 and finance_term_hits >= 1)
            or (market_moving_hits >= 2 and major_entity_hits >= 1)
            or (market_moving_hits >= 2 and any(score >= 3 for score in sector_scores.values()))
        )

        if not has_investor_signal:
            return RelevanceResult(sector=None, score=0.0, matched_keywords=[])

        if market_moving_hits:
            for sector in sector_scores:
                sector_scores[sector] += min(3, market_moving_hits)

        if major_entity_hits:
            for sector in sector_scores:
                sector_scores[sector] += min(2, major_entity_hits)

        trusted_bonus = TRUSTED_SOURCE_BONUS.get(article.source, 0)
        if trusted_bonus:
            for sector in sector_scores:
                sector_scores[sector] += trusted_bonus

        if not sector_scores:
            return RelevanceResult(sector=None, score=0.0, matched_keywords=[])

        best_sector = max(sector_scores, key=sector_scores.get)
        if sector_scores[best_sector] < 5:
            return RelevanceResult(sector=None, score=0.0, matched_keywords=[])

        return RelevanceResult(
            sector=best_sector,
            score=sector_scores[best_sector],
            matched_keywords=sorted(set(matched_keywords[best_sector])),
        )
