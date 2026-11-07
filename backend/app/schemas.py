from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    federal_district: str
    center_city: Optional[str] = None
    slug: str
    upcoming_events: int = 0


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    title: str
    url: Optional[str] = None
    tier: str


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    organizer: Optional[str] = None
    event_date: date
    event_time: Optional[time] = None
    date_time_precision: str
    event_type: str
    status: str
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    city: Optional[str] = None
    venue: Optional[str] = None
    prize_fund_amount: Optional[float] = None
    prize_fund_visibility: str
    prize_fund_note: Optional[str] = None
    registration_url: Optional[str] = None
    source_url: str
    confidence: float
    moderation: str


class EventPage(BaseModel):
    items: list[EventOut]
    total: int
    page: int
    limit: int


class StatsOut(BaseModel):
    upcoming_total: int
    upcoming_regional: int
    upcoming_national: int
    regions_with_events: int
    with_prize: int


class RawPostIn(BaseModel):
    platform: str = "telegram"
    source_title: str = "Demo"
    source_url: Optional[str] = None
    external_post_id: Optional[str] = None
    text: str
    posted_at: Optional[datetime] = None
