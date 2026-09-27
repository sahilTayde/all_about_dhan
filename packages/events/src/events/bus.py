"""Publish/subscribe event bus: in-memory (default) and Redis Streams (optional), one interface.

    bus = create_bus()                       # memory, or USE_EVENT_BUS_BACKEND=redis
    sid = bus.subscribe(["ENTRY_APPROVED"], handler, priority=10)
    bus.publish("ENTRY_APPROVED", {...}, source="boss") -> event_id
    bus.unsubscribe(sid)

Every published event is JSON-validated and appended to the audit log (if one is attached)
before any subscriber sees it. Within one event, subscribers run by (priority, subscribe order).
A subscriber that raises is logged and recorded in `bus.errors`; the others still run.

V2-02: envelope v2 on every message, one stream per topic, consumer groups, outbox publisher,
REG-06 bad-entry fix (bad entry recorded durably, good entries never skipped).
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from events.audit import EventAuditLog
from events.schema import FOUNDER_FIRST, Event, EventType, make_event

MAX_ERRORS = 1000
log = logging.getLogger("events.bus")

Handler = Callable[[Event], None]


class BadEntryStore:
    """REG-06: durable bad-entry record. First bad entry per stream/entry_id recorded once."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None or db_path == ":memory:":
            conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            path = Path(db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn = conn
        self._init_schema()
        self._lock = threading.RLock()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bad_entries (
                    entry_id TEXT PRIMARY KEY,
                    stream TEXT NOT NULL,
                    raw_data TEXT,
                    error TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                )
                """
            )

    def record(self, stream: str, entry_id: str, raw_data: bytes | str | None, error: str) -> bool:
        """Record bad entry. Returns True if newly recorded, False if already exists."""
        raw_str = raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data
        with self._lock:
            try:
                with self.conn:
                    self.conn.execute(
                        "INSERT INTO bad_entries (entry_id, stream, raw_data, error) VALUES (?, ?, ?, ?)",
                        (entry_id, stream, raw_str, error),
                    )
                log.warning("Recorded bad entry %s in stream %s: %s", entry_id, stream, error)
                return True
            except sqlite3.IntegrityError:
                # Already recorded
                return False

    def count(self, stream: str | None = None) -> int:
        with self._lock:
            if stream is None:
                row = self.conn.execute("SELECT COUNT(*) FROM bad_entries").fetchone()
                return int(row[0]) if row else 0
            row = self.conn.execute(
                "SELECT COUNT(*) FROM bad_entries WHERE stream = ?", (stream,)
            ).fetchone()
            return int(row[0]) if row else 0

    def get_all(self, stream: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if stream is None:
                rows = self.conn.execute(
                    "SELECT entry_id, stream, error, recorded_at FROM bad_entries ORDER BY recorded_at"
                ).fetchall()
            else:
                rows = self.conn.execute(
                    "SELECT entry_id, stream, error, recorded_at FROM bad_entries WHERE stream = ? ORDER BY recorded_at",
                    (stream,),
                ).fetchall()
            return [
                {"entry_id": r[0], "stream": r[1], "error": r[2], "recorded_at": r[3]} for r in rows
            ]


@dataclass(frozen=True)
class Subscription:
    sub_id: str
    event_types: frozenset[str]
    callback: Handler
    priority: int
    order: int


class EventBus:
    backend = "base"

    def __init__(self, audit: EventAuditLog | None = None, *, raise_errors: bool = False) -> None:
        self.audit = audit
        self.raise_errors = raise_errors
        self.errors: list[dict[str, Any]] = []  # capped at MAX_ERRORS: a hot failing handler cannot grow memory
        self._subs: dict[str, Subscription] = {}
        self._by_type: dict[str, list[Subscription]] = {}
        self._counter = itertools.count(1)
        self._lock = threading.RLock()

    def subscribe(self, event_types: Iterable[Any], callback: Handler, *, priority: int = 100) -> str:
        kinds = frozenset(EventType(getattr(t, "value", t)).value for t in event_types)
        n = next(self._counter)
        sub = Subscription(f"sub-{n}", kinds, callback, int(priority), n)
        with self._lock:
            self._subs[sub.sub_id] = sub
            self._reindex()
        return sub.sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        with self._lock:
            found = self._subs.pop(subscription_id, None) is not None
            self._reindex()
        return found

    def _reindex(self) -> None:
        by_type: dict[str, list[Subscription]] = {}
        for sub in sorted(self._subs.values(), key=lambda s: (s.priority, s.order)):
            for kind in sub.event_types:
                by_type.setdefault(kind, []).append(sub)
        self._by_type = by_type

    def publish(self, event_type: Any, payload: dict[str, Any] | None = None, *, source: str = "unknown") -> str:
        event = make_event(event_type, payload, source=source)
        raw = json.dumps(event.payload, separators=(",", ":"), allow_nan=False)  # JSON contract
        with self._lock:
            if self.audit is not None:
                self.audit.append(event, raw)
            self._send(event)
        return event.event_id

    def _send(self, event: Event) -> None:
        raise NotImplementedError

    def _dispatch(self, event: Event) -> None:
        for sub in self._by_type.get(event.event_type, ()):
            try:
                sub.callback(event)
            except Exception as exc:
                log.exception("subscriber %s failed on %s", sub.sub_id, event.event_type)
                self.errors.append(
                    {"sub_id": sub.sub_id, "event_type": event.event_type, "event_id": event.event_id,
                     "error": f"{type(exc).__name__}: {exc}"}
                )
                if len(self.errors) > MAX_ERRORS:
                    del self.errors[0]
                if self.raise_errors:
                    raise

    def _dispatch_batch(self, events: list[Event]) -> None:
        """Founder commands in a batch jump ahead of everything else (stable otherwise)."""
        for event in sorted(events, key=lambda e: FOUNDER_FIRST.get(e.event_type, 1)):
            self._dispatch(event)


class MemoryBus(EventBus):
    """Synchronous, in-process. `publish` returns after every subscriber ran (nested publishes
    run depth-first), so replay is deterministic. Not durable: events live only in the audit log."""

    backend = "memory"

    def _send(self, event: Event) -> None:
        self._dispatch(event)


class RedisStreamsBus(EventBus):
    """Durable transport on Redis Streams. V2-02: one stream per topic, consumer groups,
    per-entry guarded parsing (REG-06: bad entries never skip good ones). Envelope v2 support."""

    backend = "redis"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        *,
        stream_prefix: str | None = None,
        stream: str | None = None,  # Legacy: single stream (backward compat)
        consumer_group: str = "engine",
        consumer_name: str = "default",
        maxlen: int = 100_000,
        client: Any = None,
        audit: EventAuditLog | None = None,
        raise_errors: bool = False,
        start_id: str = "$",
        bad_entry_db: str | Path | None = None,
    ) -> None:
        super().__init__(audit, raise_errors=raise_errors)
        if client is None:
            import redis  # optional dependency

            client = redis.Redis.from_url(redis_url)
        self.client = client
        
        # Backward compat: old API used single 'stream', new API uses 'stream_prefix'
        if stream is not None and stream_prefix is None:
            # Legacy mode: single stream for all events
            self.stream_prefix = stream.rsplit(":", 1)[0] + ":" if ":" in stream else "events:"
            self._legacy_single_stream = stream
        else:
            self.stream_prefix = stream_prefix or "all_about_dhan:"
            self._legacy_single_stream = None
            
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name or f"consumer-{uuid.uuid4().hex[:8]}"
        self.maxlen = maxlen
        self.start_id = start_id
        
        # Replay mode: if start_id is not "$", use a unique consumer group for replay
        if start_id != "$":
            self.consumer_group = f"replay-{uuid.uuid4().hex[:12]}"
            
        self.bad_entries = BadEntryStore(bad_entry_db)
        # Track last_id per stream for consumer group resume
        self._stream_last_ids: dict[str, str] = {}
        self._lock = threading.RLock()

    def _stream_name(self, event_type: str) -> str:
        """Map event type to stream name (one stream per topic, or legacy single stream)."""
        if self._legacy_single_stream:
            return self._legacy_single_stream
        return f"{self.stream_prefix}{event_type}"

    def _ensure_consumer_group(self, stream: str) -> None:
        """Ensure consumer group exists for the stream."""
        try:
            self.client.xgroup_create(stream, self.consumer_group, id="0", mkstream=True)
            log.info("Created consumer group %s for stream %s", self.consumer_group, stream)
        except Exception as exc:  # noqa: BLE001
            # Group already exists (BUSYGROUP) or other error
            if "BUSYGROUP" not in str(exc):
                log.debug("Consumer group creation for %s: %s", stream, exc)

    def _send(self, event: Event) -> None:
        stream = self._stream_name(event.event_type)
        self._ensure_consumer_group(stream)
        self.client.xadd(stream, {"event": event.to_json()}, maxlen=self.maxlen, approximate=True)

    def _try_parse_event(self, stream: str, entry_id: str, raw: bytes | str) -> Event | None:
        """Per-entry guarded parsing (REG-06). Returns None if parse fails (bad entry recorded)."""
        try:
            return Event.from_json(raw)
        except Exception as exc:  # noqa: BLE001
            error_msg = f"{type(exc).__name__}: {exc}"
            self.bad_entries.record(stream, entry_id, raw, error_msg)
            return None

    def poll(self, *, block_ms: int | None = None, count: int = 500) -> int:
        """
        Poll for new events from all subscribed streams using consumer groups.

        REG-06: per-entry guarded parsing ensures bad entries never skip good ones.
        Uses XREADGROUP, XACK after dispatch, XPENDING/XCLAIM for recovery.
        """
        # Build stream dict: {stream: ">"}  (> = undelivered messages)
        streams = {}
        for event_type in self._by_type:
            stream = self._stream_name(event_type)
            self._ensure_consumer_group(stream)
            streams[stream] = ">"

        if not streams:
            return 0

        # XREADGROUP
        try:
            resp = self.client.xreadgroup(
                self.consumer_group,
                self.consumer_name,
                streams,
                count=count,
                block=block_ms,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("XREADGROUP failed: %s", exc)
            return 0

        batch: list[Event] = []
        ack_map: dict[str, list[str]] = {}  # {stream: [entry_id, ...]}

        for stream_bytes, entries in resp or ():
            stream = stream_bytes.decode("utf-8") if isinstance(stream_bytes, bytes) else stream_bytes
            ack_map.setdefault(stream, [])

            for entry_id_bytes, fields in entries:
                entry_id = (
                    entry_id_bytes.decode("utf-8")
                    if isinstance(entry_id_bytes, bytes)
                    else entry_id_bytes
                )
                raw = fields.get(b"event") if b"event" in fields else fields.get("event")

                # Per-entry guarded parsing (REG-06)
                event = self._try_parse_event(stream, entry_id, raw)
                if event is not None:
                    batch.append(event)
                    ack_map[stream].append(entry_id)
                # Bad entries are recorded and skipped, good ones continue

        # Dispatch batch
        if batch:
            self._dispatch_batch(batch)

        # XACK after successful dispatch
        for stream, entry_ids in ack_map.items():
            if entry_ids:
                try:
                    self.client.xack(stream, self.consumer_group, *entry_ids)
                except Exception as exc:  # noqa: BLE001
                    log.error("XACK failed for stream %s: %s", stream, exc)

        return len(batch)

    def claim_pending(self, *, idle_ms: int = 30_000, count: int = 100) -> int:
        """
        Claim pending messages that have been idle for too long (consumer crashed before XACK).

        Uses XPENDING + XCLAIM to recover messages from dead consumers.
        Returns number of messages claimed and dispatched.
        """
        claimed_count = 0
        for event_type in self._by_type:
            stream = self._stream_name(event_type)
            self._ensure_consumer_group(stream)

            try:
                # XPENDING: get pending messages
                pending = self.client.xpending_range(
                    stream, self.consumer_group, min="-", max="+", count=count
                )
            except Exception as exc:  # noqa: BLE001
                log.error("XPENDING failed for stream %s: %s", stream, exc)
                continue

            if not pending:
                continue

            # Filter by idle time
            idle_entries = [
                p["message_id"] for p in pending if p.get("time_since_delivered", 0) >= idle_ms
            ]
            if not idle_entries:
                continue

            # XCLAIM: claim idle messages
            try:
                claimed = self.client.xclaim(
                    stream,
                    self.consumer_group,
                    self.consumer_name,
                    min_idle_time=idle_ms,
                    message_ids=idle_entries,
                )
            except Exception as exc:  # noqa: BLE001
                log.error("XCLAIM failed for stream %s: %s", stream, exc)
                continue

            # Parse and dispatch claimed messages
            batch: list[Event] = []
            ack_ids: list[str] = []
            for entry_id_bytes, fields in claimed:
                entry_id = (
                    entry_id_bytes.decode("utf-8")
                    if isinstance(entry_id_bytes, bytes)
                    else entry_id_bytes
                )
                raw = fields.get(b"event") if b"event" in fields else fields.get("event")
                event = self._try_parse_event(stream, entry_id, raw)
                if event is not None:
                    batch.append(event)
                    ack_ids.append(entry_id)

            if batch:
                self._dispatch_batch(batch)
                try:
                    self.client.xack(stream, self.consumer_group, *ack_ids)
                    claimed_count += len(ack_ids)
                except Exception as exc:  # noqa: BLE001
                    log.error("XACK failed after claim for stream %s: %s", stream, exc)

        return claimed_count


def create_bus(backend: str | None = None, *, audit: EventAuditLog | None = None, **kw: Any) -> EventBus:
    """`memory` (default) or `redis` (env USE_EVENT_BUS_BACKEND / EVENT_BUS_REDIS_URL)."""
    name = (backend or os.environ.get("USE_EVENT_BUS_BACKEND") or "memory").strip().lower()
    if name == "memory":
        return MemoryBus(audit, **kw)
    if name == "redis":
        url = kw.pop("redis_url", None) or os.environ.get("EVENT_BUS_REDIS_URL") or "redis://localhost:6379/0"
        return RedisStreamsBus(url, audit=audit, **kw)
    raise ValueError(f"unknown event bus backend {name!r} (memory | redis)")
