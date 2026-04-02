from __future__ import annotations

import re
import string
from html import unescape
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from market_monitor.app.config import STOPWORDS


PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation)


def clean_whitespace(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def strip_html(value: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return clean_whitespace(unescape(text))


def normalise_text(value: str | None) -> str:
    cleaned = clean_whitespace(value).lower()
    return cleaned.translate(PUNCTUATION_TABLE)


def normalise_title(value: str | None) -> str:
    return normalise_text(value)


def canonicalise_url(url: str) -> str:
    parts = urlsplit(url.strip())
    filtered_query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.startswith("utm_") and key not in {"guccounter", "ncid"}
    ]
    normalised_path = re.sub(r"/+$", "", parts.path or "/")
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            normalised_path,
            urlencode(filtered_query, doseq=True),
            "",
        )
    )


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def split_sentences(text: str | None) -> list[str]:
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", clean_whitespace(text))
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def build_summary(texts: Iterable[str | None], max_sentences: int = 2) -> str:
    sentences: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for sentence in split_sentences(text):
            normalised = normalise_text(sentence)
            if normalised and normalised not in seen:
                sentences.append(sentence)
                seen.add(normalised)
            if len(sentences) >= max_sentences:
                return " ".join(sentences)
    return " ".join(sentences)


def tokenise(value: str | None) -> list[str]:
    text = normalise_text(value)
    return [token for token in text.split() if token and token not in STOPWORDS]


def jaccard_similarity(left: str | None, right: str | None) -> float:
    left_tokens = set(tokenise(left))
    right_tokens = set(tokenise(right))
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(intersection) / len(union)
