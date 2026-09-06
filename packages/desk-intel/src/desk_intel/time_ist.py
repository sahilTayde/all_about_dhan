"""Asia/Kolkata timestamps. Session clock is IST (see teams/03_phd_market)."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    return datetime.now(IST)


def now_ist_iso() -> str:
    return now_ist().replace(microsecond=0).isoformat()


def to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(IST)
    return dt.astimezone(IST)


def parse_hhmm(raw: str) -> time:
    parts = (raw or "09:45").strip().split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return time(hour, minute)


def in_opening_drive(until: str = "09:45", now: Optional[datetime] = None) -> bool:
    current = now or now_ist()
    clock = current.time().replace(tzinfo=None)
    return time(9, 15) <= clock <= parse_hhmm(until)


def parse_rss_datetime(raw: str) -> Optional[datetime]:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return to_ist(parsedate_to_datetime(text))
    except (TypeError, ValueError, IndexError):
        pass
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return to_ist(dt)
    except ValueError:
        return None


def within_hours(dt: Optional[datetime], hours: int, now: Optional[datetime] = None) -> bool:
    if dt is None:
        return True
    current = now or now_ist()
    return (current - dt) <= timedelta(hours=hours)
