"""Calendar provider boundary.

No holiday list is embedded here.  An unavailable provider is deliberately
unknown, and callers must hold paper direction rather than infer a holiday.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class CalendarStatus:
    date: date
    known: bool
    is_session: bool | None
    source: str
    reason: str


class CalendarProvider(Protocol):
    def status(self, day: date) -> CalendarStatus:
        ...


class UnknownCalendarProvider:
    """Safe default when no exchange calendar evidence is available."""

    def status(self, day: date) -> CalendarStatus:
        return CalendarStatus(
            date=day,
            known=False,
            is_session=None,
            source="unavailable",
            reason="calendar UNKNOWN — PAPER pause",
        )


class FixtureCalendarProvider:
    """Explicit test fixture; it is not an exchange holiday authority."""

    def __init__(self, *, session_days: set[date]) -> None:
        self.session_days = set(session_days)

    def status(self, day: date) -> CalendarStatus:
        return CalendarStatus(
            date=day,
            known=True,
            is_session=day in self.session_days,
            source="fixture",
            reason="fixture calendar only; not verified exchange data",
        )
