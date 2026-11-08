from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .api.routes import router

app = FastAPI(title="Drone Racing Aggregator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def _bootstrap_data() -> None:
    """Эфемерный диск Render: при пустой базе самозаполняемся фидом ФГДР."""
    import threading
    from datetime import datetime, timedelta, timezone

    from .database import SessionLocal
    from .models import Event, RawPost

    with SessionLocal() as s:
        empty = s.query(Event).count() == 0 and s.query(RawPost).count() == 0
    if not empty:
        return

    def run():
        try:
            from .database import SessionLocal as S2
            from .collectors.runner import run_all
            with S2() as s2:
                report = run_all(s2, limit=40)
            print(f"BOOTSTRAP collect: fgdr={report[0] if report else None} "
                  f"tg_channels={sum(1 for r in report if r.get('source','').startswith('tg:'))}", flush=True)
        except Exception as exc:
            print(f"BOOTSTRAP collect FAILED: {exc}", flush=True)
        try:
            text = (
                'Всероссийские спортивные соревнования пилотов «На высоте!» — онлайн-отбор в игре '
                'Split FPV и симуляторе Квадросим. Регистрация открыта на onf.ru/tournament. Отбор '
                'стартует 7 ноября, далее очные межрегиональные этапы и гранд-финал в июле. '
                'Организатор — Общероссийский народный фронт.'
            )
            from .importer import ingest_post
            with SessionLocal() as s:
                ev = ingest_post(
                    s, text=text, platform="vk_web", source_title="Народный фронт (VK)",
                    source_url="https://onf.ru/tournament", external_post_id="onf-navyshote",
                    posted_at=datetime.now(timezone.utc) - timedelta(days=1), force_approve=True,
                )
                if ev:
                    ev.prize_fund_note = 'Призовой фонд — миллионы рублей (гранд-финал — июль 2027)'
                    ev.prize_fund_visibility = "tbd"
                    s.commit()
                print("BOOTSTRAP onf event:", ev.id if ev else None, flush=True)
        except Exception as exc:
            print(f"BOOTSTRAP onf FAILED: {exc}", flush=True)
        with SessionLocal() as s:
            from .models import Event, RawPost
            print(f"BOOTSTRAP final: events={s.query(Event).count()} raw={s.query(RawPost).count()}", flush=True)
        print("BOOTSTRAP done", flush=True)

    threading.Thread(target=run, daemon=True).start()


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    from .seed import main as seed_main
    try:
        seed_main()
    except Exception as exc:
        print(f"SEED WARNING: {exc}")
    _bootstrap_data()


@app.get("/api/health")
def health():
    return {"status": "ok"}
