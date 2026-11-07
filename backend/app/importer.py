"""Import pipeline: raw post text -> Event (with dedup)."""
from __future__ import annotations

import hashlib
import unicodedata
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .extract import extract
from .models import Event, EventSource, RawPost, Region, Source

GENERIC_HEADERS = (
    "соревнования", "гонки", "этап", "фгдр", "кубок", "чемпионат",
    "региональные", "межрегиональные", "открытые", "внимание", "друзья",
    "частые", "анонсы", "приглашаем", "регистрация", "итоги",
)


def norm_title(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).lower().replace("ё", "е")
    t = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in t)
    words = [w for w in t.split() if w and w not in GENERIC_HEADERS]
    return " ".join(words)[:280]


def get_or_create_region(session: Session, raw_text: str) -> Region | None:
    from .region_match import match_region
    regions = session.query(Region).all()
    return match_region(regions, raw_text)


def post_hash(platform: str, source_ext_id: str, post_id: str) -> str:
    return hashlib.sha256(f"{platform}:{source_ext_id}:{post_id}".encode()).hexdigest()


def ingest_post(
    session: Session,
    text: str,
    platform: str = "telegram",
    source_title: str = "",
    source_url: str | None = None,
    external_post_id: str | None = None,
    posted_at: datetime | None = None,
    auto_approve: bool = False,
    force_approve: bool = False,
) -> Event | None:
    src_ext_id = external_post_id or hashlib.sha256((source_title + text[:120]).encode()).hexdigest()[:16]
    h = post_hash(platform, source_title or platform, src_ext_id)

    existing = session.execute(select(RawPost).where(RawPost.hash == h)).scalar_one_or_none()
    if existing:
        return None

    source = None
    if source_title:
        source = session.execute(
            select(Source).where(Source.title == source_title, Source.platform == platform)
        ).scalar_one_or_none()
        if source is None:
            source = Source(platform=platform, external_id=source_title, title=source_title, url=source_url)
            session.add(source)
            session.flush()

    ex = extract(text, now=posted_at.date() if posted_at else None)
    if posted_at and ex.event_date and ex.date_has_year is False and ex.date_bumped:
        # Дата без года «уехала» на следующий год: скорее всего это архив о
        # прошедшем старте. Возвращаем событие в год поста и помечаем как
        # завершённое — такие вещи не должны выглядеть будущими анонсами.
        candidate = ex.event_date.replace(year=posted_at.date().year)
        if candidate <= posted_at.date():
            ex.event_date = candidate
            ex.status = "finished" if ex.status == "anons" else ex.status
        else:
            ex.event_date = None
    region = get_or_create_region(session, text)

    raw = RawPost(
        source_id=source.id if source else None,
        external_post_id=src_ext_id,
        hash=h,
        text=text,
        posted_at=posted_at,
        processed=True,
        extracted_json=ex.to_dict(),
    )
    session.add(raw)

    if ex.event_date is None:
        return None

    title = ex.title or "Соревнование по дрон-рейсингу"
    norm = norm_title(title)

    evt = session.execute(
        select(Event).where(
            Event.norm_title == norm,
            Event.event_date == ex.event_date,
            Event.region_id == region.id if region else Event.region_id.is_(None),
        )
    ).scalar_one_or_none()

    if evt is None:
        evt = Event(
            title=title,
            norm_title=norm,
            event_date=ex.event_date,
            event_type=ex.event_type,
            status=ex.status,
            region_id=region.id if region else None,
            city=ex.city or (region.center_city if region else None),
            prize_fund_amount=ex.prize_amount,
            prize_fund_visibility=ex.prize_visibility,
            prize_fund_note=ex.prize_note,
            registration_url=ex.registration_url,
            source_url=ex.registration_url or source_url or "",
            source_id=source.id if source else None,
            confidence=ex.confidence,
            moderation="approved" if force_approve or (auto_approve and ex.confidence >= 0.55) else "pending",
        )
        session.add(evt)
        session.flush()

    evs = EventSource(event_id=evt.id, source_id=source.id if source else None, external_post_id=src_ext_id)
    session.add(evs)
    session.commit()
    return evt
