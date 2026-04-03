from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from market_monitor.app.config import DATABASE_URL, ensure_directories
from market_monitor.app.models import Base

ensure_directories()

engine_kwargs = {"future": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)

SQLITE_ARTICLE_MIGRATIONS: dict[str, str] = {
    "event_type": "ALTER TABLE articles ADD COLUMN event_type VARCHAR(64)",
    "impacted_assets": "ALTER TABLE articles ADD COLUMN impacted_assets VARCHAR(512)",
    "impact_direction": "ALTER TABLE articles ADD COLUMN impact_direction VARCHAR(32)",
    "impact_confidence": "ALTER TABLE articles ADD COLUMN impact_confidence FLOAT",
    "importance_score": "ALTER TABLE articles ADD COLUMN importance_score INTEGER",
    "impact_rationale": "ALTER TABLE articles ADD COLUMN impact_rationale TEXT",
    "enrichment_provider": "ALTER TABLE articles ADD COLUMN enrichment_provider VARCHAR(32)",
}


def _apply_sqlite_migrations() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as connection:
        existing_tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).all()
        }
        if "articles" not in existing_tables:
            return

        existing_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(articles)")).all()
        }
        for column_name, ddl in SQLITE_ARTICLE_MIGRATIONS.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _apply_sqlite_migrations()


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
