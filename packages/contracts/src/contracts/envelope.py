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
        Backward-compatible: accepts legacy events.schema.Event (event_type, payload, source,
        event_id, timestamp - no 'v' field). V2 fields (stream, event_ts, available_ts) are
        optional and default from 'timestamp' if missing.
        """
        # Check if V2 (has 'v' field) or legacy (no 'v' field)
        if "v" in data:
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

        # Legacy events.schema.Event: event_type, payload, source, event_id, timestamp
        # V2-specific fields default from timestamp
        return cls(
            v=1,
            event_type=data["event_type"],
            event_id=data["event_id"],
            stream=data.get("stream", "legacy"),
            source=data["source"],
            event_ts=data.get("event_ts", data["timestamp"]),
            available_ts=data.get("available_ts", data["timestamp"]),
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
