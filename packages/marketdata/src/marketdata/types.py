"""Tick / closed-bar types for the bar builder.

Kept inside ``marketdata`` so the builder does not depend on the unmerged V2-01
``contracts`` package. Field names match the V2 envelope payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marketdata.clock import IST


@dataclass(frozen=True)
class Tick:
    """One print. ``exchange_ts`` is ISO-8601 (timezone-aware preferred)."""

    instrument_id: str
    ltp: float | None
    ltq: int | None
    volume: int | None
    oi: int | None
    exchange_ts: str


@dataclass(frozen=True)
class BarClosed:
    """A finalized bar. ``available_ts`` is when the bar was closed, never before ``end``."""

    instrument_id: str
    tf: str  # "1m" | "3m" | "5m"
    start: str
    end: str
    o: float | None
    h: float | None
    l: float | None  # noqa: E741
    c: float | None
    v: int | None
    n_ticks: int
    gap: bool = False
    late_ticks: int = 0  # ticks dropped while this bar was open (event_ts before bucket start)
    available_ts: str = ""


class SimClock:
    """Replay clock. Advances only when told; never goes backwards."""

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("SimClock start must be timezone-aware")
        self._current = start

    def now(self) -> datetime:
        return self._current

    def advance_to(self, new_time: datetime) -> None:
        if new_time.tzinfo is None:
            raise ValueError("SimClock.advance_to requires timezone-aware datetime")
        if new_time < self._current:
            raise ValueError(
                f"SimClock cannot go backwards: current={self._current.isoformat()}, new_time={new_time.isoformat()}"
            )
        self._current = new_time


def parse_ts(ts_str: str) -> datetime:
    """Parse ISO-8601; naive values are treated as IST."""
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt


def bucket_start(ts: datetime) -> datetime:
    """Wall-clock minute bucket start."""
    return ts.replace(second=0, microsecond=0)
