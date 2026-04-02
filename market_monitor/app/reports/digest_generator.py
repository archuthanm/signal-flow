from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from market_monitor.app.config import (
    APP_NAME,
    MIN_RELEVANCE_FOR_DIGEST,
    OUTPUT_DIR,
    OUTPUT_FILE_TEMPLATE,
    SECTOR_DISPLAY_NAMES,
    TOP_ARTICLES_PER_SECTOR,
)
from market_monitor.app.models import Article
from market_monitor.app.processors.sector_classifier import display_sector_name


class DigestGenerator:
    def generate(self, session: Session, target_date: datetime, window_days: int | None = None) -> tuple[str, Path]:
        payload = self.build_payload(session, target_date, window_days=window_days)
        articles = payload["articles"]
        article_counts = payload["sector_counts"]
        top_overall = payload["top_stories"]
        sections: list[str] = [f"# {APP_NAME} Daily Digest - {target_date.date().isoformat()}", ""]

        sections.append("## Top Stories")
        if top_overall:
            for article in top_overall:
                sections.extend(self._render_article(article))
        else:
            sections.append("- No high-relevance stories available.")
        sections.append("")

        sections.append("## Sector Counts")
        for sector_key in SECTOR_DISPLAY_NAMES:
            sections.append(
                f"- {display_sector_name(sector_key)}: {article_counts.get(sector_key, 0)}"
            )
        sections.append("")

        for sector_key, display_name in SECTOR_DISPLAY_NAMES.items():
            sections.append(f"## {display_name}")
            sector_articles = payload["sectors"][sector_key]["articles"]
            if not sector_articles:
                sections.append("- No qualifying stories.")
                sections.append("")
                continue
            for article in sector_articles:
                sections.extend(self._render_article(article))
            sections.append("")

        themes = payload["themes"]
        sections.append("## Themes")
        if themes:
            sections.append(f"- {', '.join(themes)}")
        else:
            sections.append("- No recurring themes identified.")

        digest_text = "\n".join(sections).strip() + "\n"
        path = OUTPUT_DIR / OUTPUT_FILE_TEMPLATE.format(date=target_date.date().isoformat())
        path.write_text(digest_text, encoding="utf-8")
        return digest_text, path

    def build_payload(
        self,
        session: Session,
        target_date: datetime,
        window_days: int | None = None,
    ) -> dict[str, object]:
        query = (
            select(Article)
            .where(Article.is_duplicate.is_(False))
            .where(Article.relevance_score >= MIN_RELEVANCE_FOR_DIGEST)
        )
        if window_days is not None:
            window_start = target_date - timedelta(days=window_days)
            query = query.where(Article.published_at >= window_start)

        articles = list(
            session.scalars(
                query.order_by(desc(Article.relevance_score), desc(Article.published_at))
            )
        )
        article_counts = Counter(article.sector or "unclassified" for article in articles)
        by_sector: dict[str, list[Article]] = {sector: [] for sector in SECTOR_DISPLAY_NAMES}
        for article in articles:
            if article.sector in by_sector and len(by_sector[article.sector]) < TOP_ARTICLES_PER_SECTOR:
                by_sector[article.sector].append(article)

        return {
            "date": target_date.date().isoformat(),
            "window_days": window_days,
            "articles": articles,
            "top_stories": articles[:3],
            "sector_counts": {sector: article_counts.get(sector, 0) for sector in SECTOR_DISPLAY_NAMES},
            "sectors": {
                sector_key: {
                    "label": display_sector_name(sector_key),
                    "articles": by_sector[sector_key],
                }
                for sector_key in SECTOR_DISPLAY_NAMES
            },
            "themes": self._extract_themes(articles),
        }

    def _render_article(self, article: Article) -> list[str]:
        lines = [
            f"### {article.title}",
            f"- Source: {article.source}",
            f"- Published: {article.published_at.isoformat() if article.published_at else 'Unknown'}",
            f"- Relevance Score: {article.relevance_score:.1f}",
            f"- URL: {article.url}",
        ]
        if article.summary:
            lines.append(f"- Summary: {article.summary}")
        if article.why_it_matters:
            lines.append(f"- Why it matters: {article.why_it_matters}")
        if article.tags:
            lines.append(f"- Tags: {article.tags}")
        lines.append("")
        return lines

    def _extract_themes(self, articles: list[Article]) -> list[str]:
        counter: Counter[str] = Counter()
        for article in articles:
            if article.tags:
                for tag in [tag.strip() for tag in article.tags.split(",") if tag.strip()]:
                    counter[tag] += 1
        return [tag for tag, _ in counter.most_common(5)]
