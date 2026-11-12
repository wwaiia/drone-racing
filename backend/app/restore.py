"""Restore DB contents from a backup JSON.

Render free services have an ephemeral disk: every redeploy/restart wipes the
SQLite file. The GitHub Actions worker keeps a fresh backup.json committed to
the repo, and on boot the backend restores it so the site never goes blank.
"""
from __future__ import annotations

import os
from datetime import date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Event, Region, Source

DEFAULT_BACKUP_URL = (
    "https://raw.githubusercontent.com/wwaiia/drone-racing/main/backend/backup/backup.json"
)


def _parse_date(v) -> date | None:
    try:
        return date.fromisoformat(v)
    except Exception:
        return None


def _parse_time(v):
    if not v:
        return None
    try:
        return datetime.strptime(v[:8], "%H:%M:%S").time()
    except Exception:
        try:
            return datetime.strptime(v[:5], "%H:%M").time()
        except Exception:
            return None


def restore_from_data(session: Session, data: dict) -> dict:
    regions: dict[str, Region] = {}
    for r in data.get("regions", []):
        name = (r.get("name") or "").strip()
        if not name:
            continue
        reg = session.execute(select(Region).where(Region.name == name)).scalars().first()
        if reg is None:
            slug = r.get("slug") or name.lower().replace(" ", "-")
            reg = Region(
                name=name,
                federal_district=r.get("federal_district") or "—",
                center_city=r.get("center_city"),
                slug=slug,
                keywords=r.get("keywords") or [],
            )
            session.add(reg)
            session.flush()
        regions[name] = reg

    for s in data.get("sources", []):
        ext = s.get("external_id")
        if not ext:
            continue
        exists = session.execute(
            select(Source).where(Source.platform == s.get("platform"), Source.external_id == ext)
        ).scalars().first()
        if exists is None:
            session.add(Source(
                platform=s.get("platform") or "vk_web",
                external_id=ext,
                title=s.get("title") or ext,
                url=s.get("url"),
                tier=s.get("tier") or "regional",
                region_id=regions[s["region"]].id if s.get("region") in regions else None,
                is_active=bool(s.get("is_active", True)),
            ))
    session.flush()

    restored = skipped = 0
    for e in data.get("events", []):
        d = _parse_date(e.get("event_date"))
        if not d or not e.get("norm_title"):
            continue
        reg = regions.get(e.get("region") or "")
        conds = [Event.norm_title == e["norm_title"], Event.event_date == d]
        if reg:
            conds.append(Event.region_id == reg.id)
        else:
            conds.append(Event.region_id.is_(None))
        if session.execute(select(Event).where(*conds)).scalars().first():
            skipped += 1
            continue
        session.add(Event(
            title=e.get("title") or "Соревнование по дрон-рейсингу",
            norm_title=e["norm_title"],
            organizer=e.get("organizer"),
            description=e.get("description"),
            event_date=d,
            event_time=_parse_time(e.get("event_time")),
            date_time_precision=e.get("date_time_precision") or "exact",
            region_id=reg.id if reg else None,
            city=e.get("city"),
            venue=e.get("venue"),
            event_type=e.get("event_type") or "regional",
            discipline=e.get("discipline") or "fpv-race",
            status=e.get("status") or "anons",
            auto_status=bool(e.get("auto_status", True)),
            prize_fund_amount=e.get("prize_fund_amount"),
            prize_fund_note=e.get("prize_fund_note"),
            prize_fund_visibility=e.get("prize_fund_visibility") or "hidden",
            registration_url=e.get("registration_url"),
            source_url=e.get("source_url") or "",
            confidence=e.get("confidence") or 0.0,
            moderation=e.get("moderation") or "approved",
        ))
        restored += 1
    session.commit()
    return {"restored_events": restored, "skipped_events": skipped,
            "regions": len(regions), "sources": len(data.get("sources", []))}


def restore_from_url(session: Session, url: str | None = None) -> dict:
    url = url or os.environ.get("BACKUP_URL", DEFAULT_BACKUP_URL)
    try:
        data = httpx.get(url, timeout=60, follow_redirects=True).json()
    except Exception as exc:  # noqa: BLE001
        return {"restored_events": 0, "skipped_events": 0, "error": str(exc)[:200]}
    try:
        return restore_from_data(session, data)
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        return {"restored_events": 0, "skipped_events": 0, "error": str(exc)[:200]}
