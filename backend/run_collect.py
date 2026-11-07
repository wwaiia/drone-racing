"""CLI helper: run one collection cycle over configured sources.

    .venv\Scripts\python.exe run_collect.py
"""
import json

from app.collectors import telegram_web
from app.config import settings
from app.database import SessionLocal
from app.models import Source


def main() -> None:
    report = []
    channels = [c.strip() for c in settings.collect_channels.split(",") if c.strip()]
    with SessionLocal() as session:
        for s in session.query(Source).filter(
            Source.is_active.is_(True), Source.platform == "telegram_web",
        ).all():
            if (s.fail_count or 0) >= 3:
                continue
            if s.external_id and s.external_id not in channels:
                channels.append(s.external_id)

    for ch in channels:
        res = telegram_web.run(ch, limit=settings.collect_limit)
        print(json.dumps(res, ensure_ascii=False), flush=True)
        report.append(res)

    print(json.dumps({"channels": len(channels), "results": report}, ensure_ascii=False))


if __name__ == "__main__":
    main()
