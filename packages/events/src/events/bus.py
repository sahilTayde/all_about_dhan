"""Publish/subscribe event bus: in-memory (default) and Redis Streams (optional), one interface.

    bus = create_bus()                       # memory, or USE_EVENT_BUS_BACKEND=redis
    sid = bus.subscribe(["ENTRY_APPROVED"], handler, priority=10)
    bus.publish("ENTRY_APPROVED", {...}, source="boss") -> event_id
    bus.unsubscribe(sid)

Every published event is JSON-validated and appended to the audit log (if one is attached)
before any subscriber sees it. Within one event, subscribers run by (priority, subscribe order).
A subscriber that raises is logged and recorded in `bus.errors`; the others still run.
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

from events.audit import EventAuditLog
from events.schema import FOUNDER_FIRST, Event, EventType, make_event

MAX_ERRORS = 1000
log = logging.getLogger("events.bus")

Handler = Callable[[Event], None]


@dataclass(frozen=True)
class Subscription:
    sub_id: str
    event_types: frozenset[str]
    callback: Handler
    priority: int
    order: int


class EventBus:
    backend = "base"

    def __init__(self, audit: Optional[EventAuditLog] = None, *, raise_errors: bool = False) -> None:
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

    def publish(self, event_type: Any, payload: Optional[dict[str, Any]] = None, *, source: str = "unknown") -> str:
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
    """Durable transport on one Redis stream. `publish` = XADD; `poll()` reads new entries and
    dispatches them (founder commands first within each batch). Needs a reachable Redis server."""

    backend = "redis"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        *,
        stream: str = "all_about_dhan:events",
        maxlen: int = 100_000,
        client: Any = None,
        audit: Optional[EventAuditLog] = None,
        raise_errors: bool = False,
        start_id: str = "$",
    ) -> None:
        super().__init__(audit, raise_errors=raise_errors)
        if client is None:
            import redis  # optional dependency

            client = redis.Redis.from_url(redis_url)
        self.client = client
        self.stream = stream
        self.maxlen = maxlen
        self.last_id = start_id
        if start_id == "$":
            info = self.client.xinfo_stream(self.stream) if self.client.exists(self.stream) else None
            self.last_id = info["last-generated-id"] if info else "0-0"

    def _send(self, event: Event) -> None:
        self.client.xadd(self.stream, {"event": event.to_json()}, maxlen=self.maxlen, approximate=True)

    def poll(self, *, block_ms: Optional[int] = None, count: int = 500) -> int:
        resp = self.client.xread({self.stream: self.last_id}, count=count, block=block_ms)
        batch: list[Event] = []
        for _stream, entries in resp or ():
            for entry_id, fields in entries:
                self.last_id = entry_id
                raw = fields.get(b"event") if b"event" in fields else fields.get("event")
                batch.append(Event.from_json(raw))
        self._dispatch_batch(batch)
        return len(batch)


def create_bus(backend: Optional[str] = None, *, audit: Optional[EventAuditLog] = None, **kw: Any) -> EventBus:
    """`memory` (default) or `redis` (env USE_EVENT_BUS_BACKEND / EVENT_BUS_REDIS_URL)."""
    name = (backend or os.environ.get("USE_EVENT_BUS_BACKEND") or "memory").strip().lower()
    if name == "memory":
        return MemoryBus(audit, **kw)
    if name == "redis":
        url = kw.pop("redis_url", None) or os.environ.get("EVENT_BUS_REDIS_URL") or "redis://localhost:6379/0"
        return RedisStreamsBus(url, audit=audit, **kw)
    raise ValueError(f"unknown event bus backend {name!r} (memory | redis)")
