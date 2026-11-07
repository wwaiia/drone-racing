"""Extraction of structured event data from raw post text.

Pipeline per post:
    regex first (cheap) -> confidence boost/deduction -> optional LLM later.
Only regex is used in MVP; LLM hook is stubbed for posts with low confidence.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any

MONTHS = {
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма[йя]": 5, "июн": 6,
    "июл": 7, "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
}
MONTH_NUM = {1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая",
             6: "июня", 7: "июля", 8: "августа", 9: "сентября", 10: "октября",
             11: "ноября", 12: "декабря"}

DATE_WORD_RE = re.compile(
    r"(?:с\s+)?(\d{1,2})(?:\s*[-–…\/]\s*(\d{1,2}))?\s+(январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*"
    r"(?:\s+(\d{4})\s*г?(?:ода)?)?",
    re.IGNORECASE,
)
DATE_NUMERIC_RE = re.compile(r"(\d{1,2})\.(\d{1,2})(\.(\d{2,4}))?")
TIME_RE = re.compile(r"(?:в|с)\s+(\d{1,2}):(\d{2})", re.IGNORECASE)
YEAR_HINT_RE = re.compile(r"(\d{4})\s*г?(?:ода)?", re.IGNORECASE)

PRIZE_RE = re.compile(
    r"призов[оа][йя]?[^.\n]{0,40}?(\d[\d\s]{2,10})\s*(?:тыс(?:яч)?\.?\s*)?(₽|руб|ру\u0301бл|\bрублей\b|рубля)?",
    re.IGNORECASE,
)
NO_PRIZE_RE = re.compile(r"без\s+призов", re.IGNORECASE)
PRIZE_TBD_RE = re.compile(r"призов[оа][йя]\s+фонд\s+будет\s+(?:объяв|сообщен)", re.IGNORECASE)

REG_OPEN_RE = re.compile(
    r"регистрац\w*\s+(?:уже\s+)?открыт|открыт[ао]\s+регистрац|зарегистрирова|запись\s+открыт|"
    r"(?:по\s+)?ссылке\s+(?:для\s+)?регистрац|принимаются\s+заявк",
    re.IGNORECASE,
)
REG_CLOSED_RE = re.compile(r"регистрац\w*\s+закрыт|заверш[ae]на\s+регистрац", re.IGNORECASE)
FINISHED_RE = re.compile(
    r"итог[и]\s+(?:соревнован|гонк|этап)|результат[ы]\s+(?:соревнован|этап)|победител(?:ем|ями)\s+ст(?:ал|али)|протоколы?\s+соревнован|итогово[е-]протокол",
    re.IGNORECASE,
)
CANCELLED_RE = re.compile(r"отмен[яе]н|перенес[яе]н", re.IGNORECASE)

DISCIPLINE_SIM_RE = re.compile(
    r"симулятор|simulator|\bdcl\b|velocidrone|liftoff|uncrashed",
    re.IGNORECASE,
)

NATIONAL_RE = re.compile(
    r"чемпионат\s+россии|кубок\s+россии|всероссийск|межрегиональн|федеральн\w*\s+этап|"
    r"вс[её]\s+россия|федераци\w+\s+гонок\s+дронов\s+россии|\bфгдр\b",
    re.IGNORECASE,
)

URL_RE = re.compile(r"https?://[^\s\)\]\>|\"']+")
TG_LINK_RE = re.compile(r"(https?://)?t\.me/[A-Za-z0-9_/-]+")

TITLE_STOP_WORDS = {
    "гонк", "гонки", "гонкам", "соревновани", "соревнования", "этапа", "этап",
    "межрегиональные", "региональные", "открытые", "пойдут", "состоятся", "дрон",
    "дронов", "рейсинг", "fpv", "квадрокоптер", "по", "в", "на", "и",
}


@dataclass
class Extracted:
    title: str | None = None
    event_date: date | None = None
    event_time: str | None = None
    date_precision: str = "exact"
    date_has_year: bool = True
    event_type: str = "regional"
    region_name: str | None = None
    city: str | None = None
    venue: str | None = None
    prize_amount: int | None = None
    prize_visibility: str = "hidden"
    prize_note: str | None = None
    status: str = "anons"
    registration_url: str | None = None
    source_url: str | None = None
    urls: list[str] = field(default_factory=list)
    discipline: str = "fpv"
    date_bumped: bool = False
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.event_date:
            d["event_date"] = self.event_date.isoformat()
        return d


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower().replace("ё", "е")


def _month_num(stem: str) -> int:
    stem = stem.lower().replace("ё", "е")
    for key, num in MONTHS.items():
        if stem.startswith(key.replace("[йя]", "")):
            return num
    return 0


def extract_dates(text: str, now: date | None = None) -> tuple[date | None, str, bool, bool]:
    now = now or date.today()
    norm = _normalize(text)

    m = DATE_WORD_RE.search(norm)
    if m:
        day1 = int(m.group(1))
        day2 = m.group(2)
        month = _month_num(m.group(3))
        if not month:
            return None, "no", False, False
        year = int(m.group(4)) if m.group(4) else None
        bumped = False
        if year is None:
            candidate = date(now.year, month, day1)
            if candidate < now:
                candidate = date(now.year + 1, month, day1)
                bumped = True
            year = candidate.year
        try:
            d = date(year, month, day1)
        except ValueError:
            return None, "no", False, False
        precision = "day" if day2 else "exact"
        return d, precision, m.group(4) is not None, bumped

    for m in DATE_NUMERIC_RE.finditer(norm):
        day, month = int(m.group(1)), int(m.group(2))
        if not (1 <= month <= 12 and 1 <= day <= 31):
            continue
        year = None
        bumped = False
        if m.group(4):
            year = int(m.group(4))
            if year < 100:
                year += 2000
        if year is None:
            candidate = date(now.year, month, day)
            if candidate < now:
                candidate = date(now.year + 1, month, day)
                bumped = True
            year = candidate.year
        try:
            return date(year, month, day), "exact", m.group(3) is not None, bumped
        except ValueError:
            continue
    return None, "no", False, False


def extract_time(text: str) -> str | None:
    m = TIME_RE.search(text)
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if 0 <= hh <= 23 and 0 <= mm <= 59:
        return f"{hh:02d}:{mm:02d}"
    return None


def extract_prize(text: str) -> tuple[int | None, str, str | None]:
    if NO_PRIZE_RE.search(text):
        return 0, "none", None
    if PRIZE_TBD_RE.search(text):
        return None, "tbd", None
    m = PRIZE_RE.search(text)
    if not m:
        return None, "hidden", None

    raw_num = m.group(1).replace(" ", "").replace("\u00a0", "")
    amount = int(raw_num)
    unit = m.group(2)
    if "тыс" in (m.group(0) or "") and amount < 10_000:
        amount *= 1000
    if unit and "руб" in unit.lower() and amount > 0:
        pass
    start, end = m.span()
    note = text[max(0, start - 20): end + 40].strip()
    return amount, "amount", note


def extract_status(text: str) -> str:
    if FINISHED_RE.search(text):
        return "finished"
    if CANCELLED_RE.search(text):
        return "postponed"
    if REG_OPEN_RE.search(text):
        return "registration_open"
    if REG_CLOSED_RE.search(text):
        return "registration_closed"
    return "anons"


def extract_type(text: str) -> str:
    return "national" if NATIONAL_RE.search(text) else "regional"


def guess_title(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None
    line = text.splitlines()[0].strip().rstrip(".!?:")
    if len(line) > 140:
        cut = line.replace(". ", ".").split(".")[0].strip()
        line = cut if 10 <= len(cut) <= 140 else line[:120].rsplit(" ", 1)[0]
    if len(line) >= 5:
        return line
    return None


def extract_links(text: str) -> tuple[list[str], str | None, str | None]:
    urls = [u.rstrip(".,;:" ) for u in URL_RE.findall(text) or []]
    tg = [u if u.startswith("http") else f"https://{u}" for u in TG_LINK_RE.findall(text)]

    reg_url = None
    REG_HINT = re.compile(r"регистра|зарегистриров|запиш|билет|участник|join|form|timepad", re.IGNORECASE)
    for u in urls + tg:
        if REG_HINT.search(u or ""):
            reg_url = u
            break
    if reg_url is None and (tg or urls):
        reg_url = (tg + urls)[0]
    source_url = None
    return urls, reg_url, source_url


def extract(text: str, now: date | None = None) -> Extracted:
    d, precision, has_year, bumped = extract_dates(text, now)
    prize, prize_vis, prize_note = extract_prize(text)
    urls, reg_url, source_url = extract_links(text)

    ex = Extracted(
        title=guess_title(text),
        event_date=d,
        event_time=extract_time(text),
        date_precision=precision,
        date_has_year=has_year,
        date_bumped=bumped,
        event_type=extract_type(text),
        discipline="simulator" if DISCIPLINE_SIM_RE.search(text) else "fpv",
        prize_amount=prize,
        prize_visibility=prize_vis,
        prize_note=prize_note,
        status=extract_status(text),
        registration_url=reg_url,
        source_url=source_url,
        urls=urls,
    )
    ex.confidence = _score(ex)
    return ex


def _score(ex: Extracted) -> float:
    c = 0.0
    if ex.event_date:
        c += 0.35
        if not ex.date_has_year:
            c -= 0.10
    if ex.title:
        c += 0.20
    if ex.region_name or ex.city:
        c += 0.15
    if ex.prize_visibility in ("amount", "none"):
        c += 0.10
    if ex.status != "anons":
        c += 0.10
    if ex.registration_url:
        c += 0.10
    return round(max(0.0, min(1.0, c)), 2)


def extract_json(text: str, now: date | None = None) -> dict[str, Any]:
    return extract(text, now).to_dict()
