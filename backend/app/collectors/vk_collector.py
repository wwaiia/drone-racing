"""VK API collector: wall posts of configured groups -> importer.

Requires VK_SERVICE_TOKEN in .env. Rate limit: ~20 req/s for service token,
we stay far below it.
"""
from __future__ import annotations

from datetime import datetime, timezone

import vk_api  # type: ignore

from ..config import settings
from ..importer import ingest_post
from ..database import SessionLocal


def fetch_group_posts(group_domain: str, count: int = 50) -> list[dict]:
    api = vk_api.VkApi(token=settings.vk_service_token).get_api()
    resp = api.wall.get(domain=group_domain, count=count, extended=0)
    return resp.get("items", [])


def run(domain: str, count: int = 50) -> int:
    """Collect posts of one group into raw_posts/events. Returns imported count."""
    imported = 0
    posts = fetch_group_posts(domain, count)
    with SessionLocal() as session:
        for item in posts:
            text = item.get("text") or ""
            if len(text) < 40:
                continue
            ts = item.get("date")
            posted_at = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
            evt = ingest_post(
                session,
                text=text,
                platform="vk",
                source_title=f"vk:{domain}",
                source_url=f"https://vk.com/wall-{item.get('owner_id', '')}_{item.get('id', '')}",
                external_post_id=f"{item.get('owner_id')}_{item.get('id')}",
                posted_at=posted_at,
                auto_approve=False,
            )
            if evt:
                imported += 1
    return imported
