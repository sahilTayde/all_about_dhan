"""IST session clock. A decision at t may only see data with available_ts <= t."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, time, timedelta, timezone
from typing import TypeVar

IST = timezone(timedelta(hours=5, minutes=30))
SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)
SQUARE_OFF = time(15, 15)
FEED_FREEZE_START = time(15, 15)
FEED_FREEZE_END = time(15, 28)
NO_NEW_BEFORE = time(9, 50)
NO_NEW_AFTER = time(14, 45)
T = TypeVar("T")


class LookAheadError(ValueError):
    """Raised when a replay reads a stamp after the decision clock."""


def as_ist(ts: datetime | str) -> datetime:
    dt = ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts))
    if dt.tzinfo is None:
        raise LookAheadError("timestamp must be timezone-aware")
    return dt.astimezone(IST)


def parse_hhmm(raw: str) -> time:
    parts = raw.strip().split(":")
    return time(int(parts[0]), int(parts[1] if len(parts) > 1 else 0))


def session_date(ts: datetime) -> str:
    return as_ist(ts).date().isoformat()


def in_session(ts: datetime, start: time = SESSION_OPEN, end: time = SESSION_CLOSE) -> bool:
    clock = as_ist(ts).time()
    return start <= clock < end


def past_square_off(ts: datetime, flat: time = SQUARE_OFF) -> bool:
    return as_ist(ts).time() >= flat


def in_feed_freeze(ts: datetime) -> bool:
    clock = as_ist(ts).time()
    return FEED_FREEZE_START <= clock < FEED_FREEZE_END


class ReplayClock:
    """Monotonic paper clock. `visible` refuses future available_ts."""

    def __init__(self, now: datetime) -> None:
        self._now = as_ist(now)

    @property
    def now(self) -> datetime:
        return self._now

    def advance_to(self, ts: datetime) -> datetime:
        nxt = as_ist(ts)
        if nxt < self._now:
            raise LookAheadError(f"clock moved backwards {self._now} -> {nxt}")
        self._now = nxt
        return self._now

    def visible(self, available_ts: datetime, *, label: str = "data") -> bool:
        stamp = as_ist(available_ts)
        if stamp > self._now:
            raise LookAheadError(f"look-ahead: {label} {stamp} > clock {self._now}")
        return True

    def take_visible(self, rows: Iterable[T], available_of: Callable[[T], datetime]) -> list[T]:
        """Return rows with available_ts <= now. Future rows stay unseen."""
        out: list[T] = []
        for row in rows:
            stamp = as_ist(available_of(row))
            if stamp <= self._now:
                out.append(row)
        return out
