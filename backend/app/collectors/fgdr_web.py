"""FGDR site collector: official news feed via Tilda feeds API (no credentials).

Feed: https://feeds.tildacdn.com/api/getfeed/?recid=2345252741&feeduid=358474190231
Each post is followed to its tpost page to get full text.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup  # type: ignore

from ..config import settings
from ..importer import ingest_post
from ..database import SessionLocal

FEED_RECID = "2345252741"
FEED_UID = "358474190231"
FEED_URL = "https://feeds.tildacdn.com/api/getfeed/"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def fetch_post_text(post_url: str) -> str:
    try:
        r = httpx.get(post_url, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        r.raise_for_status()
    except Exception:
        return ""
    soup = BeautifulSoup(r.text, "html.parser")
    body = soup.find(class_="t-body") or soup.find(class_="t-feed__post-content") or soup
    text = body.get_text(" ", strip=True)
    text = re.sub(r"\\S+", " ", text)
    return text[:4000]


def _retry(fn, attempts: int = 3, base_delay: float = 2.0):
    """Tildacdn from some datacenter IPs can drop chunked responses — retry."""
    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            time.sleep(base_delay * (i + 1))
    raise last_exc


def fetch_feed_posts(limit: int = 40) -> list[dict]:
    params = {"recid": FEED_RECID, "feeduid": FEED_UID, "start": 1, "amountofposts": limit}
    r = _retry(lambda: httpx.get(FEED_URL, params=params, headers={"User-Agent": UA}, timeout=20))
    r.raise_for_status()
    data = r.json()
    posts = []
    for p in (data.get("posts") or []):
        if isinstance(p, str):
            continue
        url = p.get("url") or ""
        title = (p.get("title") or "").strip()
        if not url or len(title) < 5:
            continue
        posts.append({
            "uid": p.get("uid") or url.rsplit("/", 1)[-1],
            "title": re.sub(r"(?i)^(?:АНОНСЫ|Анонсы|Анонс)[,\s—-]*", "", title),
            "url": url,
            "date": p.get("published") or "",
        })
    return posts[:limit]


def run(limit: int = 40) -> dict:
    imported = posts_count = 0
    error = None
    try:
        posts = fetch_feed_posts(limit)
        posts_count = len(posts)
    except Exception as exc:
        return {"source": "web:fgdr.ru", "imported": 0, "posts": 0, "error": str(exc)[:200]}

    with SessionLocal() as session:
        for p in posts:
            try:
                text = _retry(lambda: fetch_post_text(p["url"]), attempts=2)
            except Exception:
                text = ""
            text = re.sub(r"(?i)^(?:\s*(?:АНОНСЫ|Анонсы|Анонс)\b[,\s—-]*)+", " ", text)
            body = text if len(text) > 80 else f"{p['title']}.\nПодробнее: {p['url']}\nИсточник: https://fgdr.ru/news/announcement"
            posted_at = None
            if p["date"]:
                try:
                    posted_at = datetime.fromisoformat(p["date"][:19]).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            evt = ingest_post(
                session,
                text=body,
                platform="web",
                source_title="web:fgdr.ru",
                source_url=p["url"],
                external_post_id=p["uid"],
                posted_at=posted_at,
                auto_approve=True,
                force_approve=True,
            )
            if evt:
                imported += 1
    return {"source": "web:fgdr.ru", "imported": imported, "posts": posts_count, "error": error}
