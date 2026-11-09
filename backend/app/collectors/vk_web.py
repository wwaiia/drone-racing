"""VK web collector: reads mobile VK (m.vk.com) community walls as anonymous
visitor via Playwright (VK blocks plain HTTP clients with badbrowser redirect).

No service token required. Rate-friendly: one page per group, few scrolls.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36")

_EXTRACT_JS = """() => {
  const links = [...document.querySelectorAll("a[href^='/wall']")];
  const posts = [];
  const seen = {};
  for (const a of links) {
    const href = a.getAttribute('href');
    if (seen[href]) continue;
    let el = a.parentElement, found = null;
    for (let i = 0; i < 12 && el; i++) {
      const t = el.textContent || '';
      const nested = el.querySelectorAll("a[href^='/wall']").length;
      if (t.length > 180 && (i < 3 || nested === 1)) found = el;
      if (t.length > 2600) break;
      el = el.parentElement;
    }
    if (found) {
      const t = (found.textContent || '').replace(/\\s+/g, ' ').trim();
      if (t.length > 60) { seen[href] = 1; posts.push({wall: href, text: t.slice(0, 3000)}); }
    }
  }
  return posts;
}"""

_NOISE_PREFIX = re.compile(r"^.*?Действия", re.S)
_NOISE_SUFFIX = re.compile(r"(Показать ещё|Отправить реакцию|Выбор реакции|Лайк).*$", re.S)
_WALL_ID = re.compile(r"^/wall(-?\d+)_(\d+)")


def _clean_text(t: str) -> str:
    t = _NOISE_PREFIX.sub("", t)
    t = _NOISE_SUFFIX.split(t)[0]
    t = re.sub(r"^\s*(Верифицировано|Министерство спорта[^ ]*)\s*", "", t)
    return t.strip()


def fetch_group_posts(domain: str, limit: int = 12, scrolls: int = 4) -> list[dict]:
    from playwright.sync_api import sync_playwright

    out: dict[str, dict] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, viewport={"width": 420, "height": 900},
                                  locale="ru-RU")
        page = ctx.new_page()
        page.goto(f"https://m.vk.com/{domain}", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)
        for _ in range(scrolls):
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            page.wait_for_timeout(1200)
            for p_ in page.evaluate(_EXTRACT_JS):
                out.setdefault(p_["wall"], p_)
                if len(out) >= limit:
                    break
            if len(out) >= limit:
                break
        # раскрыть длинные посты
        try:
            btns = page.get_by_text("Показать ещё", exact=True)
            n = btns.count()
            for i in range(min(n, 10)):
                try:
                    btns.nth(i).click(timeout=1500)
                    page.wait_for_timeout(400)
                except Exception:
                    pass
            for p_ in page.evaluate(_EXTRACT_JS):
                if p_["wall"] in out and len(p_["text"]) > len(out[p_["wall"]]["text"]):
                    out[p_["wall"]] = p_
        except Exception:
            pass
        browser.close()
    posts = []
    for wall, p_ in out.items():
        text = _clean_text(p_["text"])
        if len(text) < 40:
            continue
        m = _WALL_ID.match(wall)
        owner = m.group(1) if m else ""
        posts.append({"wall": wall, "owner": owner, "text": text})
    return posts


def run(domain: str, count: int = 12) -> dict:
    imported = 0
    error = None
    try:
        posts = fetch_group_posts(domain, limit=count)
    except Exception as exc:  # noqa: BLE001
        return {"source": f"vk_web:{domain}", "posts": 0, "imported": 0, "error": str(exc)[:160]}
    from ..database import SessionLocal

    with SessionLocal() as session:
        from ..importer import ingest_post
        for p_ in posts:
            m = re.match(r"/wall(-?\d+)_(\d+)", p_["wall"])
            post_id = f"{m.group(1)}_{m.group(2)}" if m else p_["wall"]
            evt = ingest_post(
                session,
                text=p_["text"],
                platform="vk_web",
                source_title=f"VK: {domain}",
                source_url=f"https://vk.com/wall{post_id}",
                external_post_id=post_id,
                posted_at=None,
                auto_approve=False,
            )
            if evt:
                imported += 1
    return {"source": f"vk_web:{domain}", "posts": len(posts), "imported": imported, "error": error}
