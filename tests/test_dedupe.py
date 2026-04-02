from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from market_monitor.app.filters.dedupe import DuplicateDetector
from market_monitor.app.models import Article, ArticlePayload, Base


def build_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    return session_factory()


def test_duplicate_detector_flags_exact_url_match() -> None:
    session = build_session()
    session.add(
        Article(
            title="ECB holds rates steady",
            source="Reuters",
            url="https://example.com/story",
            published_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    session.commit()

    detector = DuplicateDetector()
    is_duplicate, reason = detector.check(
        session,
        ArticlePayload(
            title="New title",
            source="Reuters",
            url="https://example.com/story",
        ),
    )

    assert is_duplicate is True
    assert reason == "duplicate_url"


def test_duplicate_detector_flags_near_duplicate_title_same_source() -> None:
    session = build_session()
    session.add(
        Article(
            title="JPMorgan boosts reserves as loan losses edge higher",
            source="Reuters",
            url="https://example.com/story-1",
            published_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    session.commit()

    detector = DuplicateDetector(similarity_threshold=0.5)
    is_duplicate, reason = detector.check(
        session,
        ArticlePayload(
            title="JPMorgan boosts reserves as loan losses rise",
            source="Reuters",
            url="https://example.com/story-2",
        ),
    )

    assert is_duplicate is True
    assert reason == "near_duplicate_title"
