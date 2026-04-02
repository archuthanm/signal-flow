from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select

from market_monitor.app.collectors.rss_collector import RSSCollector
from market_monitor.app.config import APP_NAME, MIN_RELEVANCE_FOR_DIGEST, TEMPLATE_DIR, TIMEZONE
from market_monitor.app.database import get_session, init_db
from market_monitor.app.filters.dedupe import DuplicateDetector
from market_monitor.app.filters.relevance import RelevanceScorer
from market_monitor.app.models import Article, ArticlePayload
from market_monitor.app.processors.summariser import RuleBasedSummariser
from market_monitor.app.processors.tagger import build_tags
from market_monitor.app.reports.digest_generator import DigestGenerator
from market_monitor.app.utils.logging_utils import configure_logging
from market_monitor.app.utils.text import normalise_title, strip_html

LOGGER = logging.getLogger(__name__)
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
WINDOW_PRESETS = {
    "24h": timedelta(days=1),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def ingest_articles() -> dict[str, int]:
    collector = RSSCollector()
    duplicate_detector = DuplicateDetector()
    scorer = RelevanceScorer()
    summariser = RuleBasedSummariser()

    stats = {"collected": 0, "inserted": 0, "duplicates": 0, "relevant": 0}
    articles = collector.collect()
    stats["collected"] = len(articles)
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    with get_session() as session:
        for payload in articles:
            if payload.url in seen_urls:
                stats["duplicates"] += 1
                continue

            title_key = normalise_title(payload.title)
            if title_key in seen_titles:
                stats["duplicates"] += 1
                continue

            is_duplicate, reason = duplicate_detector.check(session, payload)
            if is_duplicate:
                stats["duplicates"] += 1
                continue

            relevance = scorer.score(payload)
            payload.sector = relevance.sector
            payload.relevance_score = relevance.score
            payload.summary, payload.why_it_matters = summariser.summarise(
                payload, relevance.matched_keywords
            )
            payload.tags = build_tags(
                payload.title,
                payload.description,
                relevance.matched_keywords,
            )

            if relevance.score >= MIN_RELEVANCE_FOR_DIGEST and relevance.sector:
                stats["relevant"] += 1

            article = Article(
                title=payload.title,
                source=payload.source,
                url=payload.url,
                published_at=payload.published_at,
                description=payload.description,
                content=payload.content,
                sector=payload.sector,
                relevance_score=payload.relevance_score,
                summary=payload.summary,
                why_it_matters=payload.why_it_matters,
                tags=", ".join(payload.tags) if payload.tags else None,
                is_duplicate=False,
                duplicate_reason=reason,
            )
            session.add(article)
            seen_urls.add(payload.url)
            seen_titles.add(title_key)
            stats["inserted"] += 1

    LOGGER.info("Ingestion stats: %s", stats)
    return stats


def generate_digest() -> Path:
    generator = DigestGenerator()
    with get_session() as session:
        _, path = generator.generate(session, datetime.now(UTC).replace(tzinfo=None), window_days=1)
    LOGGER.info("Digest generated at %s", path)
    return path


def serialise_article(article: Article) -> dict[str, object]:
    title = article.title
    source_suffix = f" {article.source}".strip()
    if article.source and title.endswith(source_suffix):
        title = title[: -len(source_suffix)].strip(" -")

    description = strip_leading_source_marker(strip_html(article.description), article.source)
    content = strip_leading_source_marker(strip_html(article.content), article.source)
    payload = ArticlePayload(
        title=title,
        source=article.source,
        url=article.url,
        published_at=article.published_at,
        description=description or None,
        content=content or None,
        sector=article.sector,
        relevance_score=article.relevance_score,
    )
    matched_keywords: list[str] = []
    summariser = RuleBasedSummariser()
    summary, why_it_matters = summariser.summarise(payload, matched_keywords)
    if article.source and article.source.lower() in summary.lower():
        summary = title
    tags = article.tags or ", ".join(build_tags(title, description or None, matched_keywords)) or None

    return {
        "id": article.id,
        "title": title,
        "source": article.source,
        "url": article.url,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "description": description,
        "sector": article.sector,
        "relevance_score": article.relevance_score,
        "summary": summary,
        "why_it_matters": why_it_matters,
        "tags": tags,
    }


def strip_leading_source_marker(text: str, source: str) -> str:
    if not text or not source:
        return text
    source_variants = [source.strip(), source.strip().replace("The ", "")]
    cleaned = text
    for variant in source_variants:
        if cleaned.lower().startswith(variant.lower() + " "):
            cleaned = cleaned[len(variant):].lstrip(" :-")
        if cleaned.lower().startswith(variant.lower() + ":"):
            cleaned = cleaned[len(variant) + 1 :].lstrip(" -")
    return cleaned


def run_pipeline() -> dict[str, str | int]:
    init_db()
    stats = ingest_articles()
    digest_path = generate_digest()
    return {**stats, "digest_path": str(digest_path)}


def resolve_window(window: str) -> tuple[str, timedelta]:
    if window not in WINDOW_PRESETS:
        raise ValueError(f"Unsupported window: {window}")
    return window, WINDOW_PRESETS[window]


app = FastAPI(title=APP_NAME)
app.mount("/static", StaticFiles(directory=str(TEMPLATE_DIR.parent / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": APP_NAME,
            "timezone": TIMEZONE,
        },
    )


@app.get("/api/articles", response_class=JSONResponse)
def list_articles(
    limit: int = Query(default=50, le=200),
    window: str = Query(default="24h"),
) -> JSONResponse:
    init_db()
    _, window_delta = resolve_window(window)
    window_start = datetime.now(UTC).replace(tzinfo=None) - window_delta
    with get_session() as session:
        articles = list(
            session.scalars(
                select(Article)
                .where(Article.is_duplicate.is_(False))
                .where(Article.relevance_score >= MIN_RELEVANCE_FOR_DIGEST)
                .where(Article.published_at >= window_start)
                .order_by(desc(Article.relevance_score), desc(Article.published_at))
                .limit(limit)
            )
        )
    payload = [serialise_article(article) for article in articles]
    return JSONResponse(payload)


@app.get("/api/digest", response_class=JSONResponse)
def get_digest(window: str = Query(default="24h")) -> JSONResponse:
    init_db()
    generator = DigestGenerator()
    target_date = datetime.now(UTC).replace(tzinfo=None)
    window_key, window_delta = resolve_window(window)
    with get_session() as session:
        digest_payload = generator.build_payload(session, target_date, window_days=window_delta.days)
        _, path = generator.generate(session, target_date, window_days=window_delta.days)

    structured_payload = {
        "date": digest_payload["date"],
        "window": window_key,
        "top_stories": [serialise_article(article) for article in digest_payload["top_stories"]],
        "sector_counts": digest_payload["sector_counts"],
        "themes": digest_payload["themes"],
        "sectors": {
            sector_key: {
                "label": sector_data["label"],
                "articles": [serialise_article(article) for article in sector_data["articles"]],
            }
            for sector_key, sector_data in digest_payload["sectors"].items()
        },
    }
    return JSONResponse(
        {
            "path": str(path),
            "content": path.read_text(encoding="utf-8"),
            "digest": structured_payload,
        }
    )


@app.post("/api/run", response_class=JSONResponse)
def trigger_run() -> JSONResponse:
    result = run_pipeline()
    return JSONResponse(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Market Monitor pipeline.")
    parser.add_argument(
        "command",
        choices=["init-db", "ingest", "digest", "run", "serve"],
        help="Command to execute.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    return parser


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    init_db()

    if args.command == "init-db":
        LOGGER.info("Database initialised.")
        return
    if args.command == "ingest":
        ingest_articles()
        return
    if args.command == "digest":
        generate_digest()
        return
    if args.command == "run":
        run_pipeline()
        return
    if args.command == "serve":
        uvicorn.run(
            "market_monitor.app.main:app",
            host=args.host,
            port=args.port,
            reload=False,
        )


if __name__ == "__main__":
    main()
