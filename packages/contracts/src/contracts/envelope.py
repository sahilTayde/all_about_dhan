"""
V2 Event Envelope: extends legacy events.schema.Event with v2-required fields.

Writer: requires event_ts, available_ts, stream.
Reader: forward-compatible (tolerates extra keys) and backward-compatible (from_json handles v1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Envelope:
    """
    V2 event envelope (extends events.schema.Event schema).

    Writer strictly requires v2 fields (event_ts, available_ts, stream).
    Reader tolerates unknown keys (forward compatible) and handles v=None for legacy events.
    """

    v: int  # 2 for V2, None for legacy events.schema.Event
    ts: str
    role: str
    event_id: str
    input_event_id: str | None
    typ: str
    pl: dict[str, Any]
    # V2-required fields
    event_ts: str
    available_ts: str
    stream: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Envelope:
        """
        Load Envelope from JSON dict.

        Forward-compatible: tolerates unknown keys in data.
        Backward-compatible: accepts legacy Event (v=None, missing event_ts/available_ts/stream).
        """
        # For legacy events, fill v2 fields with fallback values
        return cls(
            v=data.get("v", 1),  # Legacy events had no v field, default to 1
            ts=data["ts"],
            role=data["role"],
            event_id=data["event_id"],
            input_event_id=data.get("input_event_id"),
            typ=data["typ"],
            pl=data["pl"],
            event_ts=data.get("event_ts", data["ts"]),  # Fallback to ts for legacy
            available_ts=data.get("available_ts", data["ts"]),  # Fallback to ts for legacy
            stream=data.get("stream", "legacy"),  # Default stream for legacy events
        )

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON dict (only v2 fields, always v=2)."""
        return {
            "v": 2,
            "ts": self.ts,
            "role": self.role,
            "event_id": self.event_id,
            "input_event_id": self.input_event_id,
            "typ": self.typ,
            "pl": self.pl,
            "event_ts": self.event_ts,
            "available_ts": self.available_ts,
            "stream": self.stream,
        }
