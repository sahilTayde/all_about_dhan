"""Typed event envelope. Every event is JSON: {event_type, event_id, timestamp, source, payload}."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

IST = timezone(timedelta(hours=5, minutes=30))


class EventType(str, Enum):
    PRE_MARKET_SUMMARY = "PRE_MARKET_SUMMARY"  # pre-market -> boss
    MARKET_TICK = "MARKET_TICK"  # feed -> desk (MTM first), boss
    REQUEST_VOTES = "REQUEST_VOTES"  # boss -> analysts
    ANALYST_VOTE = "ANALYST_VOTE"  # analysts -> boss
    ENTRY_APPROVED = "ENTRY_APPROVED"  # boss -> desk
    NO_ENTRY = "NO_ENTRY"  # boss -> audit (why no ticket)
    EXIT_APPROVED = "EXIT_APPROVED"  # boss/founder -> desk
    ORDER_SUBMITTED = "ORDER_SUBMITTED"  # desk -> monitor, boss
    ORDER_FILLED = "ORDER_FILLED"  # desk -> monitor, boss
    ORDER_CANCELLED = "ORDER_CANCELLED"  # desk -> monitor, boss
    POSITION_UPDATE = "POSITION_UPDATE"  # desk -> monitor, boss
    POSITION_CLOSED = "POSITION_CLOSED"  # desk -> monitor, boss, post-market
    ENTRY_VETOED = "ENTRY_VETOED"  # desk (risk engine / founder pause) -> boss, founder
    HEALTH_ALERT = "HEALTH_ALERT"  # monitor/desk -> founder, boss
    FOUNDER_COMMAND = "FOUNDER_COMMAND"  # founder -> desk, boss; highest priority
    REGIME_LABEL = "REGIME_LABEL"  # regime service -> boss, audit (minute label change / intermarket)
    BOSS_SHADOW = "BOSS_SHADOW"  # boss -> audit: adaptive-weight / overlay decision next to the static one


FOUNDER_FIRST = {EventType.FOUNDER_COMMAND.value: 0}


def now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class Event:
    event_type: str
    payload: dict[str, Any]
    source: str = "unknown"
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = field(default_factory=now_iso)

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_json(cls, raw: str | bytes) -> "Event":
        return cls(**json.loads(raw))


def make_event(event_type: Any, payload: Any = None, *, source: str = "unknown") -> Event:
    """Validated event. Unknown types and non-JSON payloads raise (ValueError / TypeError)."""
    kind = EventType(event_type.value if isinstance(event_type, EventType) else str(event_type)).value
    body = {} if payload is None else payload
    if not isinstance(body, dict):
        raise TypeError(f"{kind}: payload must be a dict, got {type(body).__name__}")
    return Event(event_type=kind, payload=body, source=str(source))
