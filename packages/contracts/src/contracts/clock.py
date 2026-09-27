"""Clock: SimClock and LiveClock for event time vs wall time."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


class Clock(Protocol):
    """Clock protocol for engine time (event time, not wall time)."""

    def now(self) -> datetime:
        """Return current engine time."""
        ...


class LiveClock:
    """Wall-clock time in IST."""

    def now(self) -> datetime:
        """Return current wall time in IST."""
        return datetime.now(IST)


class SimClock:
    """Simulated clock for replay and testing. Advances only when told to."""

    def __init__(self, start: datetime) -> None:
        """Initialize at start time."""
        if start.tzinfo is None:
            raise ValueError("SimClock start must be timezone-aware")
        self._current = start

    def now(self) -> datetime:
        """Return current simulated time."""
        return self._current

    def advance_to(self, new_time: datetime) -> None:
        """
        Advance clock to new_time.

        Raises:
            ValueError: if new_time is before current time (time cannot go backwards)
                       or if new_time is naive (no timezone)
        """
        if new_time.tzinfo is None:
            raise ValueError("SimClock.advance_to requires timezone-aware datetime")
        if new_time < self._current:
            raise ValueError(
                f"SimClock cannot go backwards: current={self._current.isoformat()}, "
                f"new_time={new_time.isoformat()}"
            )
        self._current = new_time

    def advance_by(self, delta: timedelta) -> None:
        """
        Advance clock by delta.

        Raises:
            ValueError: if delta is negative (time cannot go backwards)
        """
        if delta < timedelta(0):
            raise ValueError(f"SimClock.advance_by refuses negative delta: {delta}")
        self._current += delta
