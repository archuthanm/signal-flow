from __future__ import annotations

from market_monitor.app.config import COMMON_FINANCE_TERMS
from market_monitor.app.utils.text import normalise_text


def build_tags(title: str, description: str | None, matched_keywords: list[str], limit: int = 5) -> list[str]:
    text = normalise_text(" ".join([title, description or ""]))
    tags: list[str] = []

    for keyword in matched_keywords:
        cleaned = keyword.strip().title()
        if cleaned and cleaned not in tags:
            tags.append(cleaned)

    for term in COMMON_FINANCE_TERMS:
        if term in text:
            cleaned = term.title()
            if cleaned not in tags:
                tags.append(cleaned)
        if len(tags) >= limit:
            break

    return tags[:limit]
