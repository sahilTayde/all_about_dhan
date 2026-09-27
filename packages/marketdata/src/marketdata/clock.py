"""Injectable clock and NSE session window. All recorder time goes through a Clock."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol

IST = timezone(timedelta(hours=5, minutes=30))
# NSE/BSE cash and F&O continuous session (same as the V2-01 India adapter).
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


class Clock(Protocol):
    def now(self) -> datetime:
        """Timezone-aware current time."""
        ...

    async def sleep(self, seconds: float) -> None: ...


class LiveClock:
    def now(self) -> datetime:
        return datetime.now(IST)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


def iso(ts: datetime) -> str:
    """RFC 3339 in IST with milliseconds, e.g. 2026-09-28T10:01:01.230+05:30."""
    return ts.astimezone(IST).isoformat(timespec="milliseconds")


def at(day: date, t: time) -> datetime:
    return datetime.combine(day, t, tzinfo=IST)


def session_day(now: datetime) -> date:
    """The weekday session that has not closed yet (today, or the next weekday).

    Exchange holidays are not known here; on a holiday the feed is silent and the
    recorder still stops at the close.
    """
    local = now.astimezone(IST)
    day = local.date()
    if local.time() >= MARKET_CLOSE:
        day += timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def market_open(day: date) -> datetime:
    return at(day, MARKET_OPEN)


def market_close(day: date) -> datetime:
    return at(day, MARKET_CLOSE)
