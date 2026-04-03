from __future__ import annotations

import re

from market_monitor.app.config import MAJOR_MARKET_ENTITIES, MARKET_MOVING_TERMS, MAX_SUMMARY_SENTENCES
from market_monitor.app.models import ArticlePayload
from market_monitor.app.processors.sector_classifier import display_sector_name
from market_monitor.app.utils.text import build_summary, clean_whitespace, normalise_text, split_sentences


class RuleBasedSummariser:
    def summarise(self, article: ArticlePayload, matched_keywords: list[str]) -> tuple[str, str]:
        title = clean_whitespace(article.title)
        description = clean_whitespace(article.description)
        content = clean_whitespace(article.content)
        combined = normalise_text(" ".join(part for part in [title, description, content] if part))

        summary = self._compose_summary(title, description, content, matched_keywords, article.source)

        sector_display = display_sector_name(article.sector)
        focus = self._extract_focus_points(combined, matched_keywords)
        why_it_matters = self._build_why_it_matters(sector_display, focus)
        return summary, why_it_matters

    def _compose_summary(
        self,
        title: str,
        description: str,
        content: str,
        matched_keywords: list[str],
        source: str,
    ) -> str:
        lead = self._normalise_sentence(description)
        if self._is_low_information_lead(lead, source):
            lead = self._normalise_sentence(title)
        if self._should_prepend_title(title, lead, matched_keywords):
            lead = f"{self._normalise_sentence(title)} {lead}"
        detail = self._pick_detail_sentence(description, content, matched_keywords, title)

        if detail and normalise_text(detail) != normalise_text(lead):
            summary = f"{lead} {detail}"
        else:
            summary = lead

        return self._trim_summary(summary)

    def _trim_summary(self, summary: str, max_words: int = 38) -> str:
        words = clean_whitespace(summary).split()
        if len(words) <= max_words:
            return " ".join(words)
        return " ".join(words[:max_words]).rstrip(".,;:") + "..."

    def _pick_detail_sentence(
        self,
        description: str,
        content: str,
        matched_keywords: list[str],
        title: str,
    ) -> str:
        candidates = split_sentences(description) + split_sentences(content)
        if not candidates:
            fallback = build_summary([description, content, title], max_sentences=max(1, MAX_SUMMARY_SENTENCES))
            return self._normalise_sentence(fallback)

        ranked = sorted(
            candidates,
            key=lambda sentence: self._sentence_score(sentence, matched_keywords, title),
            reverse=True,
        )
        for sentence in ranked:
            cleaned = self._normalise_sentence(sentence)
            if (
                cleaned
                and len(cleaned.split()) >= 6
                and normalise_text(cleaned) != normalise_text(title)
            ):
                return cleaned
        return ""

    def _sentence_score(self, sentence: str, matched_keywords: list[str], title: str) -> tuple[int, int, int]:
        text = normalise_text(sentence)
        keyword_hits = sum(1 for keyword in matched_keywords if keyword.lower() in text)
        entity_hits = sum(1 for entity in MAJOR_MARKET_ENTITIES if entity in text)
        catalyst_hits = sum(1 for catalyst in MARKET_MOVING_TERMS if catalyst in text)
        title_overlap = len(set(normalise_text(title).split()) & set(text.split()))
        return (keyword_hits + entity_hits + catalyst_hits, catalyst_hits + entity_hits, title_overlap)

    def _normalise_sentence(self, sentence: str) -> str:
        cleaned = clean_whitespace(sentence)
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        return cleaned

    def _should_prepend_title(self, title: str, lead: str, matched_keywords: list[str]) -> bool:
        title_text = normalise_text(title)
        lead_text = normalise_text(lead)
        if not lead_text:
            return True

        title_focus_hits = sum(
            1 for keyword in matched_keywords if keyword.lower() in title_text and keyword.lower() not in lead_text
        )
        title_entity_hits = sum(
            1 for entity in MAJOR_MARKET_ENTITIES if entity in title_text and entity not in lead_text
        )
        title_catalyst_hits = sum(
            1 for catalyst in MARKET_MOVING_TERMS if catalyst in title_text and catalyst not in lead_text
        )
        return (title_focus_hits + title_entity_hits + title_catalyst_hits) > 0

    def _is_low_information_lead(self, lead: str, source: str) -> bool:
        lead_text = normalise_text(lead)
        source_text = normalise_text(source)
        return (
            not lead_text
            or len(lead_text.split()) < 5
            or lead_text == source_text
        )

    def _extract_focus_points(self, combined_text: str, matched_keywords: list[str]) -> list[str]:
        focus_points: list[str] = []

        for keyword in matched_keywords:
            cleaned = keyword.strip().lower()
            if cleaned and cleaned not in focus_points:
                focus_points.append(cleaned)

        for entity in MAJOR_MARKET_ENTITIES:
            if entity in combined_text and entity not in focus_points:
                focus_points.append(entity)

        for catalyst in MARKET_MOVING_TERMS:
            if catalyst in combined_text and catalyst not in focus_points:
                focus_points.append(catalyst)

        return focus_points[:3]

    def _build_why_it_matters(self, sector_display: str, focus_points: list[str]) -> str:
        if sector_display == "Unclassified":
            return (
                "This is worth monitoring because it adds context to the broader market narrative, "
                "even if it is not a core digest driver."
            )

        if not focus_points:
            return (
                f"This matters for {sector_display.lower()} because it may shift how investors "
                f"price the sector in the near term."
            )

        if len(focus_points) == 1:
            focus_text = focus_points[0]
        elif len(focus_points) == 2:
            focus_text = f"{focus_points[0]} and {focus_points[1]}"
        else:
            focus_text = f"{focus_points[0]}, {focus_points[1]}, and {focus_points[2]}"
        if sector_display == "Macro / Rates":
            return (
                f"This matters for {sector_display.lower()} because it can shift the path investors price for "
                f"policy, yields, and the dollar through {focus_text}."
            )
        if sector_display == "Banking":
            return (
                f"This matters for {sector_display.lower()} because it can change expectations for earnings, "
                f"funding conditions, and balance-sheet risk through {focus_text}."
            )
        if sector_display == "Fintech":
            return (
                f"This matters for {sector_display.lower()} because it can affect payments volumes, regulatory "
                f"pressure, and growth expectations through {focus_text}."
            )
        return (
            f"This matters for {sector_display.lower()} because it changes the market read on "
            f"{focus_text} and could affect positioning, expectations, or sentiment."
        )
