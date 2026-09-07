"""Deterministic paper-runtime safety hooks.

These guards are intentionally independent of personas, LLM output, and broker
clients.  A guard can only hold/reject a paper signal; it cannot enable an
execution path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class SafetyState:
    paper_paused: bool = False
    stale_data: bool = False
    malformed_payload: bool = False
    calendar_unknown: bool = False
    duplicate: bool = False
    error: bool = False
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def kill_switch(self) -> bool:
        return any(
            (
                self.paper_paused,
                self.stale_data,
                self.malformed_payload,
                self.calendar_unknown,
                self.duplicate,
                self.error,
            )
        )

    @classmethod
    def from_flags(
        cls,
        *,
        paper_paused: bool = False,
        stale_data: bool = False,
        malformed_payload: bool = False,
        calendar_unknown: bool = False,
        duplicate: bool = False,
        error: bool = False,
        reasons: Iterable[str] = (),
    ) -> "SafetyState":
        flags = (
            ("PAPER_PAUSED", paper_paused),
            ("STALE_DATA", stale_data),
            ("MALFORMED_PAYLOAD", malformed_payload),
            ("CALENDAR_UNKNOWN", calendar_unknown),
            ("DUPLICATE", duplicate),
            ("RUNTIME_ERROR", error),
        )
        merged = list(reasons)
        merged.extend(name for name, enabled in flags if enabled and name not in merged)
        return cls(
            paper_paused=paper_paused,
            stale_data=stale_data,
            malformed_payload=malformed_payload,
            calendar_unknown=calendar_unknown,
            duplicate=duplicate,
            error=error,
            reasons=tuple(dict.fromkeys(merged)),
        )


def validate_freshness(status: str) -> bool:
    """Only explicit freshness states are accepted at a persistence boundary."""
    return status in {"FRESH", "FIXTURE", "STALE", "UNKNOWN"}
