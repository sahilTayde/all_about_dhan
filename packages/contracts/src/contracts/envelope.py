"""Envelope v2: compatible with events.schema.Event, extends with new fields."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

IST = timezone(timedelta(hours=5, minutes=30))


def now_iso() -> str:
    """Return current time in IST as ISO-8601 string with milliseconds."""
    return datetime.now(IST).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class Envelope:
    """
    V2 event envelope, compatible with events.schema.Event.

    Old fields kept; new fields optional in reader, required in writer.
    """

    # Required fields (compatible with Event)
    event_type: str
    payload: dict[str, Any]
    source: str = "unknown"
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = field(default_factory=now_iso)

    # V2 new fields
    v: int = 2
    stream: str | None = None
    event_ts: str | None = None
    available_ts: str | None = None
    account_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_json(cls, raw: str | bytes) -> Envelope:
        """Deserialize from JSON string, compatible with old Event format."""
        data = json.loads(raw)
        # Handle old Event format (no v field or v=1)
        if "v" not in data:
            data["v"] = 1
        return cls(**data)
