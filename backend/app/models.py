from datetime import date, datetime, time, timezone

from sqlalchemy import (
    String, Text, Integer, BigInteger, Boolean, Date, Time, Float, Numeric,
    ForeignKey, UniqueConstraint, Index, DateTime, JSON, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def BIGPK():
    return BigInteger().with_variant(Integer(), "sqlite")


def utcnow():
    return datetime.now(timezone.utc)


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    federal_district: Mapped[str] = mapped_column(String(60), nullable=False)
    center_city: Mapped[str | None] = mapped_column(String(120))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    keywords: Mapped[list | None] = mapped_column(JSON, default=list)

    events: Mapped[list["Event"]] = relationship(back_populates="region")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(400))
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="regional")
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fail_count: Mapped[int] = mapped_column(Integer, default=0)

    posts: Mapped[list["RawPost"]] = relationship(back_populates="source")


class RawPost(Base):
    __tablename__ = "raw_posts"
    __table_args__ = (UniqueConstraint("hash", name="uq_raw_posts_hash"),)

    id: Mapped[int] = mapped_column(BIGPK(), primary_key=True, autoincrement=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    external_post_id: Mapped[str | None] = mapped_column(String(120))
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assets: Mapped[list | None] = mapped_column(JSON, default=list)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    extracted_json: Mapped[dict | None] = mapped_column(JSON)

    source: Mapped[Source | None] = relationship(back_populates="posts")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("norm_title", "event_date", "region_id", name="uq_events_dedup"),
        Index("ix_events_type_date", "event_type", "event_date"),
        Index("ix_events_region_date", "region_id", "event_date"),
    )

    id: Mapped[int] = mapped_column(BIGPK(), primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    norm_title: Mapped[str] = mapped_column(String(300), nullable=False)
    organizer: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)

    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_time: Mapped[time | None] = mapped_column(Time)
    date_time_precision: Mapped[str] = mapped_column(String(10), default="exact")

    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), index=True)
    region: Mapped[Region | None] = relationship(back_populates="events")
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    venue: Mapped[str | None] = mapped_column(String(200))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)

    event_type: Mapped[str] = mapped_column(String(10), nullable=False, default="regional")
    discipline: Mapped[str] = mapped_column(String(20), default="fpv-race")

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="anons", index=True)
    auto_status: Mapped[bool] = mapped_column(Boolean, default=True)

    prize_fund_amount: Mapped[int | None] = mapped_column(Numeric(12, 2))
    prize_fund_currency: Mapped[str] = mapped_column(String(8), default="RUB")
    prize_fund_note: Mapped[str | None] = mapped_column(Text)
    prize_fund_visibility: Mapped[str] = mapped_column(String(10), default="hidden")

    registration_url: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))

    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    moderation: Mapped[str] = mapped_column(String(10), default="pending", index=True)
    moderation_note: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    event_sources: Mapped[list["EventSource"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EventSource(Base):
    __tablename__ = "event_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    external_post_id: Mapped[str | None] = mapped_column(String(120))
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    event: Mapped[Event] = relationship(back_populates="event_sources")
