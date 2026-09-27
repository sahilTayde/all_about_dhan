"""
V2 Event Envelope: extends legacy events.schema.Event with v2-required fields.

Spec: Section 4.4 - V2 envelope with event_type, source, payload (not typ/role/pl).
Writer: requires event_ts, available_ts, stream, source.
Reader: forward-compatible (tolerates extra keys) and backward-compatible
(from_json handles legacy events.schema.Event).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Envelope:
    """
    V2 event envelope (extends events.schema.Event schema, section 4.4).

    Writer strictly requires v2 fields (event_type, source, event_ts, available_ts, stream).
    Reader tolerates unknown keys (forward compatible) and handles legacy events.schema.Event
    (with typ/role/pl instead of event_type/source/payload).
    """

    v: int  # 2 for V2 events
    event_type: str
    event_id: str
    stream: str
    source: str
    event_ts: str
    available_ts: str
    timestamp: str
    account_id: str | None
    correlation_id: str | None
    causation_id: str | None
    payload: dict[str, Any]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Envelope:
        """
        Load Envelope from JSON dict.

        Forward-compatible: tolerates unknown keys in data.
        Backward-compatible: accepts legacy events.schema.Event with typ/role/pl/ts fields.
        """
        # Legacy Event fields: typ, role, pl, ts (no event_ts/available_ts/stream)
        # V2 fields: event_type, source, payload, timestamp (plus event_ts/available_ts/stream)

        # Handle legacy events.schema.Event (typ/role/pl/ts)
        if "typ" in data:
            # Legacy event: map old fields to new
            return cls(
                v=data.get("v", 1),  # Legacy events have no v field
                event_type=data["typ"],  # typ -> event_type
                event_id=data["event_id"],
                stream=data.get("stream", "legacy"),  # Default stream for legacy
                source=data.get("role", "unknown"),  # role -> source
                event_ts=data.get("event_ts", data["ts"]),  # Fallback to ts
                available_ts=data.get("available_ts", data["ts"]),  # Fallback to ts
                timestamp=data.get("timestamp", data["ts"]),  # timestamp = ts for legacy
                account_id=data.get("account_id"),
                correlation_id=data.get("correlation_id")
                or data.get("input_event_id"),  # input_event_id -> correlation_id
                causation_id=data.get("causation_id"),
                payload=data.get("pl", {}),  # pl -> payload
            )

        # V2 event: use fields as-is
        return cls(
            v=data["v"],
            event_type=data["event_type"],
            event_id=data["event_id"],
            stream=data["stream"],
            source=data["source"],
            event_ts=data["event_ts"],
            available_ts=data["available_ts"],
            timestamp=data["timestamp"],
            account_id=data.get("account_id"),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            payload=data["payload"],
        )

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON dict (V2 format, always v=2)."""
        return {
            "v": 2,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "stream": self.stream,
            "source": self.source,
            "event_ts": self.event_ts,
            "available_ts": self.available_ts,
            "timestamp": self.timestamp,
            "account_id": self.account_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": self.payload,
        }
