from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    description: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[str | None] = mapped_column(String(64), index=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    why_it_matters: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(String(512))
    event_type: Mapped[str | None] = mapped_column(String(64))
    impacted_assets: Mapped[str | None] = mapped_column(String(512))
    impact_direction: Mapped[str | None] = mapped_column(String(32))
    impact_confidence: Mapped[float | None] = mapped_column(Float)
    importance_score: Mapped[int | None] = mapped_column(Integer)
    impact_rationale: Mapped[str | None] = mapped_column(Text)
    enrichment_provider: Mapped[str | None] = mapped_column(String(32))
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    duplicate_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now_naive, nullable=False
    )


@dataclass(slots=True)
class ArticlePayload:
    title: str
    source: str
    url: str
    published_at: datetime | None = None
    description: str | None = None
    content: str | None = None
    sector: str | None = None
    relevance_score: float = 0.0
    summary: str | None = None
    why_it_matters: str | None = None
    tags: list[str] = field(default_factory=list)
    is_duplicate: bool = False
    duplicate_reason: str | None = None
