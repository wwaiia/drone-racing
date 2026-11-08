"""Telegram public web collector: reads https://t.me/s/<channel> HTML.

No Telegram account, no API keys — works from any worldwide hosting.
"""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup  # type: ignore

from ..config import settings
from ..importer import ingest_post
from ..database import SessionLocal

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def _proxy():
    return None


def fetch_channel_posts(channel: str, limit: int = 40) -> list[dict]:
    url = f"https://t.me/s/{channel}"
    resp = httpx.get(url, headers={"User-Agent": UA}, timeout=httpx.Timeout(8.0, connect=8.0), proxy=_proxy(), follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    posts: list[dict] = []
    for msg in soup.select("div.tgme_widget_message_wrap"):
        holder = msg.select_one("div.tgme_widget_message")
        if holder is None:
            continue
        data_post = holder.get("data-post") or ""
        if "/" not in data_post:
            continue
        post_id = data_post.rsplit("/", 1)[1].strip()
        text_node = msg.select_one("div.tgme_widget_message_text")
        text = text_node.get_text(" ", strip=True) if text_node else ""
        if len(text) < 40:
            continue
        time_node = msg.select_one("time")
        dt = time_node.get("datetime") if time_node else None
        posts.append({
            "id": post_id,
            "text": text,
            "date": dt,
            "url": f"https://t.me/{channel}/{post_id}",
        })
    return posts[:limit]


def run(channel: str, limit: int = 40) -> dict:
    """Collect one public channel into raw_posts/events."""
    imported = errors = 0
    try:
        posts = fetch_channel_posts(channel, limit)
    except Exception as exc:
        return {"source": f"tg:{channel}", "imported": 0, "posts": 0, "error": str(exc)[:200]}

    with SessionLocal() as session:
        for p in posts:
            evt = ingest_post(
                session,
                text=p["text"],
                platform="telegram",
                source_title=f"tg:{channel}",
                source_url=p["url"],
                external_post_id=p["id"],
                auto_approve=True,
            )
            if evt:
                imported += 1
    return {"source": f"tg:{channel}", "imported": imported, "posts": len(posts), "error": None}
