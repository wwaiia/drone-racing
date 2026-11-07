"""Match extracted text fragment to a known region by keywords."""
from __future__ import annotations

import re


def norm(text: str) -> str:
    return text.lower().replace("ё", "е") if text else ""


def match_region(regions: list, text: str):
    """regions: iterable of Region with .name/.keywords; text: raw post text."""
    t = norm(text)
    best = None
    best_pos = len(t)
    best_len = 0
    for r in regions:
        for kw in r.keywords or []:
            pattern = r"(?<![a-zа-яё])" + re.escape(norm(kw))
            m = re.search(pattern, t)
            if not m:
                continue
            pos = m.start()
            kwl = len(kw)
            if pos < best_pos or (pos == best_pos and kwl > best_len):
                best, best_pos, best_len = r, pos, kwl
                break
    return best
