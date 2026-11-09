from datetime import date
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Event, Region, Source
from ..schemas import EventOut, EventPage, RegionOut, StatsOut
from ..config import settings
from ..extract import PAST_TENSE_RE

router = APIRouter(prefix="/api/v1")

# состояние фонового сбора (одного экземпляра достаточно)
COLLECT_STATE: dict = {}


def auto_recompute_status(db: Session) -> None:
    today = date.today()
    for evt in db.query(Event).filter(
        Event.auto_status.is_(True),
        Event.moderation == "approved",
        Event.status.in_(["anons", "registration_open", "registration_closed", "ongoing"]),
    ).all():
        if evt.event_date < today:
            evt.status = "finished"
        elif evt.event_date == today:
            evt.status = "ongoing"


def to_out(evt: Event) -> EventOut:
    return EventOut(
        id=evt.id,
        title=evt.title,
        organizer=evt.organizer,
        event_date=evt.event_date,
        event_time=evt.event_time,
        date_time_precision=evt.date_time_precision,
        event_type=evt.event_type,
        status=evt.status,
        region_id=evt.region_id,
        region_name=evt.region.name if evt.region else None,
        city=evt.city,
        venue=evt.venue,
        prize_fund_amount=float(evt.prize_fund_amount) if evt.prize_fund_amount is not None else None,
        prize_fund_visibility=evt.prize_fund_visibility,
        prize_fund_note=evt.prize_fund_note,
        registration_url=evt.registration_url,
        source_url=evt.source_url,
        confidence=evt.confidence,
        moderation=evt.moderation,
    )


@router.get("/regions", response_model=list[RegionOut])
def list_regions(db: Session = Depends(get_db), only_with_events: bool = False):
    auto_recompute_status(db)
    rows = db.execute(
        select(
            Region,
            func.count(Event.id).label("cnt"),
        )
        .join(Event, (Event.region_id == Region.id) & (Event.moderation == "approved") & (Event.event_date >= date.today()))
        .group_by(Region.id)
    ).all()
    result = []
    for region, cnt in rows:
        result.append(RegionOut(
            id=region.id, name=region.name, federal_district=region.federal_district,
            center_city=region.center_city, slug=region.slug, upcoming_events=cnt,
        ))
    if only_with_events:
        result = [r for r in result if r.upcoming_events > 0]
    result.sort(key=lambda r: -r.upcoming_events)
    return result


@router.get("/events")
def list_events(
    db: Session = Depends(get_db),
    mode: str = Query("all", pattern="^(regional|national|all|by_region)$"),
    region_id: int | None = None,
    status: str | None = Query(None, pattern="^(anons|registration_open|registration_closed|ongoing|finished|postponed|cancelled)$"),
    has_prize: bool | None = None,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    only_upcoming: bool = True,
    page: int = 1,
    limit: int = Query(20, le=100),
):
    auto_recompute_status(db)
    stmt = select(Event).where(Event.moderation == "approved")

    if mode == "national":
        stmt = stmt.where(Event.event_type == "national")
    elif mode == "regional":
        stmt = stmt.where(Event.event_type == "regional")
    elif mode == "by_region":
        stmt = stmt.where(Event.event_type == "regional")
        if region_id:
            stmt = stmt.where(Event.region_id == region_id)

    if region_id and mode != "by_region":
        stmt = stmt.where(Event.region_id == region_id)
    if status:
        stmt = stmt.where(Event.status == status)
    if has_prize is not None:
        if has_prize:
            stmt = stmt.where(Event.prize_fund_amount > 0)
        else:
            stmt = stmt.where(or_(Event.prize_fund_amount.is_(None), Event.prize_fund_amount == 0))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Event.title.ilike(like), Event.city.ilike(like), Event.organizer.ilike(like)))
    if only_upcoming:
        stmt = stmt.where(Event.event_date >= date.today())
    else:
        if date_from:
            stmt = stmt.where(Event.event_date >= date_from)
        if date_to:
            stmt = stmt.where(Event.event_date <= date_to)

    stmt = stmt.order_by(Event.event_date.asc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.offset((max(page, 1) - 1) * limit).limit(limit)
    ).scalars().all()

    return EventPage(items=[to_out(e) for e in rows], total=total, page=page, limit=limit)


@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    evt = db.get(Event, event_id)
    if not evt:
        raise HTTPException(404, "Event not found")
    return to_out(evt)


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    auto_recompute_status(db)
    today = date.today()
    def base_counts():
        return db.query(Event).filter(Event.moderation == "approved", Event.event_date >= today)
    q1 = base_counts()
    regions_cnt = q1.filter(Event.region_id.isnot(None)).with_entities(Event.region_id).distinct().count()
    return StatsOut(
        upcoming_total=base_counts().count(),
        upcoming_regional=base_counts().filter(Event.event_type == "regional").count(),
        upcoming_national=base_counts().filter(Event.event_type == "national").count(),
        regions_with_events=regions_cnt,
        with_prize=base_counts().filter(Event.prize_fund_amount > 0).count(),
    )


@router.post("/admin/events/{event_id}/approve")
def approve_event(event_id: int, db: Session = Depends(get_db), x_admin_token: str = Header("")):
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")
    evt = db.get(Event, event_id)
    if not evt:
        raise HTTPException(404, "Event not found")
    evt.moderation = "approved"
    db.commit()
    return {"id": evt.id, "moderation": evt.moderation}


@router.post("/admin/events/{event_id}/reject")
def reject_event(event_id: int, db: Session = Depends(get_db), x_admin_token: str = Header("")):
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")
    evt = db.get(Event, event_id)
    if not evt:
        raise HTTPException(404, "Event not found")
    evt.moderation = "rejected"
    db.commit()
    return {"id": evt.id, "moderation": evt.moderation}


@router.post("/admin/run_collect")
def run_collect(
    db: Session = Depends(get_db),
    limit: int = Query(40, le=200),
    x_admin_token: str = Header(""),
):
    """Collect all configured sources asynchronously; poll /admin/collect_status."""
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")

    import threading
    from ..collectors.runner import run_all

    COLLECT_STATE.clear()
    COLLECT_STATE.update({"running": True, "started": time.time()})

    def _job() -> None:
        from ..database import SessionLocal
        with SessionLocal() as session:
            try:
                rep = run_all(session, limit=limit)
                COLLECT_STATE["report"] = rep
            except Exception as exc:  # noqa: BLE001
                COLLECT_STATE["report"] = [{"source": "runner", "posts": 0, "imported": 0,
                                            "error": str(exc)[:200]}]
            finally:
                COLLECT_STATE["running"] = False

    threading.Thread(target=_job, daemon=True).start()
    return {"started": True, "status_url": "/api/v1/admin/collect_status"}


@router.get("/admin/collect_status")
def collect_status(x_admin_token: str = Header("")):
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")
    return {"running": COLLECT_STATE.get("running", False),
            "report": COLLECT_STATE.get("report"),
            "elapsed_sec": round(time.time() - COLLECT_STATE.get("started", time.time()))}


@router.post("/admin/sources")
def admin_add_source(
    platform: str = Query(..., pattern="^(telegram_web|telegram|vk|vk_web|web|max_web)$"),
    external_id: str = "",
    title: str = "",
    url: str = "",
    db: Session = Depends(get_db),
    x_admin_token: str = Header(""),
):
    """Register a source for periodic collection (cron-based run_collect uses it)."""
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")
    src = db.query(Source).filter(
        Source.platform == platform, Source.external_id == external_id
    ).first()
    if src:
        src.is_active = True
        db.commit()
        return {"id": src.id, "status": "re-activated"}
    src = Source(platform=platform, external_id=external_id, title=title or external_id, url=url or None)
    db.add(src)
    db.commit()
    return {"id": src.id, "status": "created"}


@router.get("/admin/sources")
def admin_list_sources(db: Session = Depends(get_db), x_admin_token: str = Header("")):
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")
    rows = db.query(Source).filter(Source.is_active.is_(True)).all()
    return [{"id": s.id, "platform": s.platform, "external_id": s.external_id,
             "title": s.title, "fail_count": s.fail_count} for s in rows]


@router.post("/admin/raw-posts")
def admin_raw_post(
    text: str,
    db: Session = Depends(get_db),
    platform: str = "telegram",
    source_title: str = "manual",
    external_post_id: str | None = None,
    source_url: str | None = None,
    x_admin_token: str = Header(""),
    auto_approve: bool = False,
):
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")
    from datetime import datetime as _dt
    from ..importer import ingest_post
    posted_at = None
    if external_post_id:
        posted_at = _dt.now()
    evt = ingest_post(db, text=text, platform=platform, source_title=source_title,
                      source_url=source_url, external_post_id=external_post_id,
                      posted_at=posted_at, auto_approve=auto_approve)
    if evt:
        return {"created_event_id": evt.id, "title": evt.title, "date": evt.event_date.isoformat(), "confidence": evt.confidence}
    return {"created_event_id": None}


@router.post("/admin/clean_titles")
def admin_clean_titles(db: Session = Depends(get_db), x_admin_token: str = Header("")):
    """Re-run title noise cleanup over stored events (safe: skips duplicates)."""
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")
    from ..extract import _clean_title_line
    from ..importer import norm_title

    changed = 0
    for evt in db.query(Event).all():
        nt = _clean_title_line(evt.title).rstrip(".!?:")
        if not nt or nt == evt.title or len(nt) < 5:
            continue
        norm = norm_title(nt)
        dup = db.query(Event).filter(
            Event.norm_title == norm,
            Event.event_date == evt.event_date,
            Event.region_id == evt.region_id,
            Event.id != evt.id,
        ).first()
        if dup:
            continue
        evt.title = nt
        evt.norm_title = norm
        changed += 1
    db.commit()
    return {"changed": changed}


@router.post("/admin/fix_past_tense")
def admin_fix_past_tense(db: Session = Depends(get_db), x_admin_token: str = Header("")):
    """Events dated in the future but described in past tense are archive posts
    that got their year bumped by the extractor. Pull them back to this year."""
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")
    today = date.today()
    changed = 0
    for evt in db.query(Event).filter(Event.event_date >= today).all():
        if not PAST_TENSE_RE.search(evt.title or ""):
            continue
        try:
            evt.event_date = evt.event_date.replace(year=today.year)
        except ValueError:
            continue
        evt.status = "finished"
        changed += 1
    db.commit()
    return {"changed": changed}


@router.post("/admin/drop_far_vk")
def admin_drop_far_vk(
    days: int = 90,
    db: Session = Depends(get_db),
    x_admin_token: str = Header(""),
):
    """Delete events dated too far ahead — old archive posts whose year got
    bumped because the post date was unknown (VK hides it from guests)."""
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")
    from datetime import timedelta
    from ..models import EventSource

    cutoff = date.today() + timedelta(days=days)
    ids = [row[0] for row in db.query(Event.id).filter(Event.event_date > cutoff).all()]
    if ids:
        db.query(EventSource).filter(EventSource.event_id.in_(ids)).delete(synchronize_session=False)
        db.query(Event).filter(Event.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    return {"dropped": len(ids)}
