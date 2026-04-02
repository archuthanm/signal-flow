from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from market_monitor.app.models import Article, Base
from market_monitor.app.reports.digest_generator import DigestGenerator


def build_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    return session_factory()


def test_digest_contains_sector_and_top_sections(tmp_path, monkeypatch) -> None:
    session = build_session()
    session.add_all(
        [
            Article(
                title="Fed prepares markets for slower cuts",
                source="Reuters",
                url="https://example.com/1",
                published_at=datetime.now(UTC).replace(tzinfo=None),
                sector="macro_rates",
                relevance_score=9,
                summary="Summary one.",
                why_it_matters="Why it matters one.",
                tags="Fed, Inflation",
            ),
            Article(
                title="Stripe expands into treasury tooling for businesses",
                source="CNBC",
                url="https://example.com/2",
                published_at=datetime.now(UTC).replace(tzinfo=None),
                sector="fintech",
                relevance_score=8,
                summary="Summary two.",
                why_it_matters="Why it matters two.",
                tags="Stripe, Fintech",
            ),
        ]
    )
    session.commit()

    monkeypatch.setattr(
        "market_monitor.app.reports.digest_generator.OUTPUT_DIR",
        tmp_path,
    )

    digest_text, path = DigestGenerator().generate(session, datetime(2026, 4, 2))

    assert path.exists()
    assert "# Market Monitor Daily Digest - 2026-04-02" in digest_text
    assert "## Top Stories" in digest_text
    assert "## Macro / Rates" in digest_text
    assert "## Fintech" in digest_text
