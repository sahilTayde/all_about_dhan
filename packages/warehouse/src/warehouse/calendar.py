"""NSE trading-day calendar. Weekends plus the committed holiday YAML. Paper only."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
_DATE = re.compile(r"(20\d{2}-\d{2}-\d{2})")


class NonTradingDay(ValueError):
    """Explicit or derived session is a weekend or listed NSE holiday."""


def holiday_yaml_path() -> Path:
    here = Path(__file__).resolve()
    for root in here.parents:
        candidate = root / "config" / "v2" / "calendar" / "nse_holidays_2026.yaml"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("config/v2/calendar/nse_holidays_2026.yaml")


@lru_cache(maxsize=1)
def nse_holidays_2026() -> frozenset[date]:
    days: set[date] = set()
    in_holidays = False
    for raw in holiday_yaml_path().read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0]
        if not line.strip():
            continue
        if line.lstrip().startswith("holidays:"):
            in_holidays = True
            continue
        if not in_holidays or "date:" not in line:
            continue
        found = _DATE.search(line)
        if found:
            days.add(date.fromisoformat(found.group(1)))
    return frozenset(days)


def is_nse_trading_day(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    return day not in nse_holidays_2026()


def as_ist(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("timestamps must be tz-aware")
    return ts.astimezone(IST)


def trading_date_from_now(now: datetime) -> date:
    """IST calendar date of `now`. A US-CT evening is already the next IST date."""
    return as_ist(now).date()


def resolve_trading_day(session: date | str | None, now: datetime) -> date:
    if session is None:
        day = trading_date_from_now(now)
    elif isinstance(session, str):
        day = date.fromisoformat(session)
    else:
        day = session
    if not is_nse_trading_day(day):
        raise NonTradingDay(f"not an NSE trading day: {day.isoformat()}")
    return day
