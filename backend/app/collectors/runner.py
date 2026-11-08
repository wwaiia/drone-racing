"""Common runner: full collection cycle (FGDR feed + Telegram web channels).

Used by /admin/run_collect and the cold-start bootstrap.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .config import settings
from .models import Event, Source


def run_all(db: Session, limit: int = 40) -> list[dict]:
    from .collectors import fgdr_web, telegram_web

    report: list[dict] = []

    res = fgdr_web.run(limit=limit)
    report.append(res)

    active = db.query(Source).filter(Source.is_active.is_(True)).all()

    tg_channels: set[str] = set(
        s.external_id for s in active
        if s.platform == "telegram_web" and s.external_id and (s.fail_count or 0) < 3
    )
    for ch in (settings.collect_channels.split(",") if settings.collect_channels else []):
        if ch.strip():
            tg_channels.add(ch.strip())

    for ch in sorted(tg_channels):
        res = telegram_web.run(ch, limit=limit)
        if res.get("error"):
            src = db.query(Source).filter(
                Source.platform == "telegram_web", Source.external_id == ch
            ).first()
            if src:
                src.fail_count = (src.fail_count or 0) + 1
                db.commit()
        report.append(res)

    # Автомодерация: уверенные события публикуются сразу
    db.query(Event).filter(
        Event.moderation == "pending",
        Event.confidence >= 0.55,
    ).update({"moderation": "approved"}, synchronize_session=False)
    db.commit()
    return report
