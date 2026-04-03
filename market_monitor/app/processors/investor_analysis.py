from __future__ import annotations

from dataclasses import dataclass

from market_monitor.app.models import ArticlePayload
from market_monitor.app.processors.sector_classifier import display_sector_name
from market_monitor.app.utils.text import normalise_text

EVENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "earnings": ("earnings", "results", "revenue", "profit", "guidance", "forecast"),
    "central_bank": ("fed", "federal reserve", "ecb", "bank of england", "rate cut", "rate hike"),
    "regulation": ("regulation", "regulatory", "antitrust", "sanctions", "lawsuit", "stress test"),
    "deal_activity": ("acquisition", "merger", "takeover", "buyout"),
    "funding": ("funding", "capital raise", "ipo", "share sale"),
    "markets": ("bond yields", "treasury", "dollar", "gold", "oil", "trading"),
}

ASSET_KEYWORDS: dict[str, tuple[str, ...]] = {
    "JPMorgan": ("jpmorgan",),
    "Goldman Sachs": ("goldman sachs",),
    "Morgan Stanley": ("morgan stanley",),
    "HSBC": ("hsbc",),
    "Wells Fargo": ("wells fargo",),
    "PayPal": ("paypal",),
    "Block": ("block", "square"),
    "Stripe": ("stripe",),
    "Visa": ("visa",),
    "Mastercard": ("mastercard",),
    "Gold": ("gold", "bullion"),
    "Oil": ("oil", "crude", "brent", "wti"),
    "US Dollar": ("dollar", "dxy", "usd"),
    "Treasury Yields": ("treasury", "bond yields", "10-year yield", "yields"),
    "Bank Stocks": ("banking", "lender", "bank stocks"),
    "Fintech Stocks": ("fintech", "payments", "digital payments"),
}

POSITIVE_TERMS = (
    "beat",
    "beats",
    "boost",
    "gain",
    "gains",
    "growth",
    "improve",
    "improves",
    "raises guidance",
    "resilient",
    "rises",
    "surge",
    "upgrades",
)

NEGATIVE_TERMS = (
    "antitrust",
    "cuts outlook",
    "decline",
    "declines",
    "downgrade",
    "fall",
    "falls",
    "fine",
    "lawsuit",
    "miss",
    "misses",
    "pressure",
    "risk",
    "slump",
    "warning",
)


@dataclass(slots=True)
class InvestorAnalysis:
    event_type: str
    impacted_assets: list[str]
    direction: str
    confidence: float
    importance_score: int
    rationale: str


class InvestorAnalyzer:
    def analyse(self, article: ArticlePayload) -> InvestorAnalysis:
        text = normalise_text(" ".join(part for part in [article.title, article.description, article.content] if part))
        event_type = self._event_type(text)
        impacted_assets = self._impacted_assets(text, article.sector)
        direction = self._direction(text, event_type)
        confidence = self._confidence(text, impacted_assets, event_type)
        importance_score = self._importance(article.relevance_score, impacted_assets, event_type, text)
        rationale = self._rationale(article, event_type, impacted_assets, direction)

        return InvestorAnalysis(
            event_type=event_type,
            impacted_assets=impacted_assets,
            direction=direction,
            confidence=confidence,
            importance_score=importance_score,
            rationale=rationale,
        )

    def _event_type(self, text: str) -> str:
        scores = {
            label: sum(1 for keyword in keywords if keyword in text)
            for label, keywords in EVENT_KEYWORDS.items()
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "general_market"

    def _impacted_assets(self, text: str, sector: str | None) -> list[str]:
        assets = [asset for asset, keywords in ASSET_KEYWORDS.items() if any(keyword in text for keyword in keywords)]
        if assets:
            return assets[:4]

        if sector == "macro_rates":
            return ["Treasury Yields", "US Dollar"]
        if sector == "banking":
            return ["Bank Stocks"]
        if sector == "fintech":
            return ["Fintech Stocks"]
        return ["Broad Equities"]

    def _direction(self, text: str, event_type: str) -> str:
        positive_hits = sum(1 for term in POSITIVE_TERMS if term in text)
        negative_hits = sum(1 for term in NEGATIVE_TERMS if term in text)

        if event_type == "central_bank":
            if "rate cut" in text and "inflation" not in text:
                positive_hits += 1
            if "rate hike" in text or "inflation" in text:
                negative_hits += 1

        if positive_hits and negative_hits:
            return "mixed"
        if positive_hits:
            return "positive"
        if negative_hits:
            return "negative"
        return "neutral"

    def _confidence(self, text: str, impacted_assets: list[str], event_type: str) -> float:
        signal = len(impacted_assets)
        signal += 1 if event_type != "general_market" else 0
        signal += 1 if any(term in text for term in POSITIVE_TERMS + NEGATIVE_TERMS) else 0
        return min(0.95, 0.45 + (signal * 0.12))

    def _importance(self, relevance_score: float, impacted_assets: list[str], event_type: str, text: str) -> int:
        importance = int(round(relevance_score))
        importance += min(2, len(impacted_assets) - 1)
        if event_type in {"earnings", "central_bank", "regulation", "deal_activity"}:
            importance += 2
        if "guidance" in text or "rate hike" in text or "rate cut" in text or "merger" in text:
            importance += 1
        return min(10, max(1, importance))

    def _rationale(
        self,
        article: ArticlePayload,
        event_type: str,
        impacted_assets: list[str],
        direction: str,
    ) -> str:
        assets = ", ".join(impacted_assets[:2])
        sector_display = display_sector_name(article.sector).lower()
        direction_text = {
            "positive": "supports",
            "negative": "pressures",
            "mixed": "creates mixed implications for",
            "neutral": "adds context for",
        }[direction]
        return f"{event_type.replace('_', ' ').title()} signal that {direction_text} {assets} within {sector_display}."
