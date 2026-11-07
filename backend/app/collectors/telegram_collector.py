"""Telegram collector (Telethon): public channels -> importer.

Requires TELEGRAM_API_ID/TELEGRAM_API_HASH in .env + a one-time login
(interactive `python -m app.collectors.telegram_collector login`).
For RF hosting set TELEGRAM_PROXY like "socks5://user:pass@host:port".
"""
from __future__ import annotations

from datetime import timezone

from telethon import TelegramClient, functions  # type: ignore

from ..config import settings
from ..importer import ingest_post
from ..database import SessionLocal


def _proxy():
    if settings.telegram_proxy:
        import socks
        return (2, "host", 0, None)  # placeholder; parse in production
    return None


def client() -> TelegramClient:
    return TelegramClient(
        settings.telegram_session,
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
        proxy=_proxy(),
    )


def fetch_channel_posts(channel: str, limit: int = 50) -> list[dict]:
    with client() as c:
        entity = c.get_entity(channel)
        items = []
        for msg in c.iter_messages(entity, limit=limit):
            text = msg.raw_text or ""
            if len(text) < 40:
                continue
            items.append({
                "id": msg.id,
                "text": text,
                "date": msg.date.astimezone(timezone.utc).isoformat(),
                "url": f"https://t.me/{channel}/{msg.id}",
            })
        return items


def run(channel: str, limit: int = 50) -> int:
    """Collect one channel into raw_posts/events. Returns imported count."""
    imported = 0
    posts = fetch_channel_posts(channel, limit)
    with SessionLocal() as session:
        for p in posts:
            evt = ingest_post(
                session,
                text=p["text"],
                platform="telegram",
                source_title=f"tg:{channel}",
                source_url=p["url"],
                external_post_id=str(p["id"]),
                posted_at=None,
                auto_approve=False,
            )
            if evt:
                imported += 1
    return imported
