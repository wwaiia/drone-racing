"""VK wall collector worker (runs in GitHub Actions, not on Render).

Scrapes public VK community walls as anonymous visitor via Playwright
(m.vk.com), then pushes cleaned post texts to the cloud backend
`/api/v1/admin/raw-posts`, where they are extracted into events.

Usage (from repo root):
    API_BASE=https://drone-racing-backend.onrender.com \
    ADMIN_TOKEN=... python backend/scripts/vk_collect.py [--limit 8] [--only a,b]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.source_data import EXTRA_SOURCES, REGIONAL_SOURCES  # noqa: E402
from app.collectors.vk_web import fetch_group_posts  # noqa: E402


def vk_domains() -> list[str]:
    out: list[str] = []
    for _region, vk_id, _tg in REGIONAL_SOURCES:
        if vk_id:
            out.append(vk_id)
    for s in EXTRA_SOURCES:
        if s.get("platform") == "vk_web" and s.get("external_id"):
            out.append(s["external_id"])
    # dedupe, сохраняя порядок
    seen: set[str] = set()
    uniq = []
    for d in out:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--only", default="")
    ap.add_argument("--base", default=os.environ.get("API_BASE", "https://drone-racing-backend.onrender.com"))
    ap.add_argument("--token", default=os.environ.get("ADMIN_TOKEN", ""))
    ap.add_argument("--sleep", type=float, default=1.5)
    args = ap.parse_args()

    if not args.token:
        print("ADMIN_TOKEN is required", file=sys.stderr)
        return 2

    domains = vk_domains()
    if args.only:
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        domains = [d for d in domains if d in want]

    print(f"VK groups: {len(domains)}")
    H = {"X-Admin-Token": args.token}
    total_posts = total_events = total_err = 0

    with httpx.Client(base_url=args.base, timeout=60, headers=H) as client:
        for i, dom in enumerate(domains, 1):
            try:
                posts = fetch_group_posts(dom, limit=args.limit)
            except Exception as exc:  # noqa: BLE001
                total_err += 1
                print(f"[{i}/{len(domains)}] {dom}: SCRAPE ERROR {str(exc)[:120]}")
                continue
            made = 0
            for p in posts:
                import re
                m = re.match(r"/wall(-?\d+)_(\d+)", p["wall"])
                post_id = f"{m.group(1)}_{m.group(2)}" if m else p["wall"]
                try:
                    r = client.post("/api/v1/admin/raw-posts", params={
                        "text": p["text"][:6000],
                        "platform": "vk_web",
                        "source_title": f"VK: {dom}",
                        "external_post_id": post_id,
                        "source_url": f"https://vk.com/wall{post_id}",
                        "auto_approve": "true",
                    })
                    if r.status_code == 200 and r.json().get("created_event_id"):
                        made += 1
                except Exception as exc:  # noqa: BLE001
                    print(f"  post {post_id}: PUSH ERROR {str(exc)[:100]}")
                time.sleep(0.15)
            total_posts += len(posts)
            total_events += made
            print(f"[{i}/{len(domains)}] {dom}: posts={len(posts)} events={made}")
            time.sleep(args.sleep)

    print(f"SUMMARY: groups={len(domains)} posts={total_posts} events={total_events} scrape_errors={total_err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
