"""Seed regions + demo raw posts on first run."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .database import Base, SessionLocal
from .importer import ingest_post
from .models import Event, Region, Source
from .region_data import REGIONS

DEMO_POSTS = [
    ("ФГДР События", "demo-1", "telegram",
     "24 ноября 2026 года в 10:00 на аэродроме Липецк-Южный (Липецкая область) пройдут открытые "
     "региональные соревнования по дрон-рейсингу. Регистрация открыта до 18 ноября — "
     "https://forms.gle/lipetsk-fgdr. Призовой фонд 120 000 ₽ за счёт спонсоров."),
    ("Drones VRN", "demo-2", "vk",
     "21.11.2026 в 12:30 Воронеж (парк «ВГТУ-Аэро»): открытый этап Воронежской области по гонкам на "
     "FPV-дронах. Регистрация по ссылке https://timepad.ru/vrn-drone. Без призового фонда, победителям "
     "разыгрываем оборудование."),
    ("ФГДР События", "demo-3", "telegram",
     "ВНИМАНИЕ! 5 декабря 2026 года в 11:00, Казань: чемпионат России по гонкам дронов FPV — финал "
     "национального уровня. Призовой фонд 500 000 ₽. Регистрация открыта: https://reg.fgdr.ru/national"),
    ("Дроны СПб", "demo-4", "telegram",
     "Санкт-Петербург, 12 декабря 2026, аэродром Горская. Региональные соревнования по дрон-рейсингу "
     "для начинающих и профи. Призовой фонд будет объявлен к 1 декабря. Запись открыта — "
     "https://t.me/drones_spb_reg"),
    ("Дроны Севера", "demo-5", "vk",
     "19 декабря 2026 года в 14:00 Архангельск, площадка «Динамика». Открытые региональные гонки "
     "дронов. Открытая регистрация: https://archangelsk-drone.ru/reg. Призовой фонд уточняется."),
    ("Regions FPV KZN", "demo-6", "telegram",
     "Челябинск: 28 ноября 2026 в 09:00 на стадионе «Строитель» — межрегиональные соревнования по "
     "полётам на квадрокоптерах. Призовой фонд 80 000 рублей. Зарегистрироваться: "
     "https://forms.yandex.ru/u/chelgado/"),
    ("Ufa Drone Racing", "demo-7", "telegram",
     "Уфа — 13 декабря 2026 — региональные гонки дронов. Призовой фонд 60 000 ₽, 1-е место — новый "
     "биокоптер. Ссылка на регистрацию: https://ufa-drone.ru/join"),
]


def seed_regions(session: Session) -> None:
    if session.query(Region).count() == 0:
        for name, district, center, lat, lng, slug, keywords in REGIONS:
            session.add(Region(name=name, federal_district=district, center_city=center,
                               lat=lat, lng=lng, slug=slug, keywords=keywords))
        session.commit()


def seed_sources(session: Session) -> tuple[int, int]:
    """Register all official FGDR sources (federal + regional) — idempotent."""
    from .source_data import FEDERAL_SOURCES, REGIONAL_SOURCES, EXTRA_SOURCES

    created = updated = 0
    region_by_name = {r.name: r for r in session.query(Region).all()}

    # миграция старых источников: API-платформы -> web-варианты (работают без токенов)
    for old, new in (("vk", "vk_web"), ("telegram", "telegram_web")):
        moved = session.query(Source).filter(Source.platform == old).all()
        for src in moved:
            twin = session.query(Source).filter(
                Source.platform == new, Source.external_id == src.external_id
            ).first()
            if twin is None:
                src.platform = new
            else:
                session.delete(src)
        session.commit()

    specs = [(s["platform"], s["external_id"], s["title"], s["url"], s["tier"], None)
             for s in FEDERAL_SOURCES]
    for region_name, vk_id, tg_id in REGIONAL_SOURCES:
        region = region_by_name.get(region_name)
        if tg_id:
            specs.append(("telegram_web", tg_id, f"ФГДР {region_name}", f"https://t.me/{tg_id}", "regional", region.id if region else None))
        if vk_id:
            specs.append(("vk_web", vk_id, f"ФГДР {region_name} (VK)", f"https://vk.com/{vk_id}", "regional", region.id if region else None))
    for s in EXTRA_SOURCES:
        region = region_by_name.get(s.get("region")) if s.get("region") else None
        specs.append((s["platform"], s["external_id"], s["title"], s["url"], s["tier"], region.id if region else None))

    for platform, ext_id, title, url, tier, region_id in specs:
        src = session.query(Source).filter(
            Source.platform == platform, Source.external_id == ext_id
        ).first()
        if src is None:
            session.add(Source(platform=platform, external_id=ext_id, title=title,
                               url=url, tier=tier))
            created += 1
        elif src.region_id or True:
            if not src.is_active:
                src.is_active = True
                updated += 1
    session.commit()
    return created, updated


def seed_demo_posts(session: Session) -> tuple[int, int]:
    from .config import settings
    if not settings.seed_demo or session.query(Event).count() > 0:
        return 0, 0
    created = skipped = 0
    now = datetime.now(timezone.utc)
    for src_title, ext_id, platform, text in DEMO_POSTS:
        res = ingest_post(session, text=text, platform=platform, source_title=src_title,
                          external_post_id=ext_id, posted_at=now - timedelta(days=5),
                          auto_approve=True)
        created += 1 if res else 0
        skipped += 0 if res else 1
    return created, skipped


def main() -> None:
    from .database import engine
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed_regions(session)
        created, updated = seed_sources(session)
        events_before = session.query(Event).count()
        post_created, post_skipped = seed_demo_posts(session)
        print(f"SEED: regions={session.query(Region).count()} sources={session.query(Source).count()} "
              f"(sources created={created} reactivated={updated}) "
              f"events={events_before + post_created} demo_posts created={post_created} skipped={post_skipped}")


if __name__ == "__main__":
    main()
