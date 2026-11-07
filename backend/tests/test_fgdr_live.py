"""Local e2e test: FGDR site feed collection (t.me works from non-RF hosting only)."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.collectors import fgdr_web

res = fgdr_web.run(limit=30)
print(res)

from app.database import SessionLocal
from app.models import Event, RawPost

with SessionLocal() as s:
    events = s.query(Event).filter(Event.source_id.isnot(None)).all()
    print(f"events total: {s.query(Event).count()}, from sources: {len(events)}")
    for e in events[-15:]:
        reg = e.region.name if e.region else None
        print(f"  #{e.id} | {e.event_date} | {reg} | {e.event_type} | {e.status} | "
              f"prize={e.prize_fund_amount}/{e.prize_fund_visibility} | conf={e.confidence} | {e.title[:70]}")
    print("raw_posts total:", s.query(RawPost).count())
