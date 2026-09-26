# events (PR-006)

Typed JSON events on a publish/subscribe bus. Every published event is appended to an append-only
SQLite `events` table (`EventAuditLog`) before any subscriber sees it.

```python
from events import EventAuditLog, MemoryBus
bus = MemoryBus(EventAuditLog(ledger.conn))        # or create_bus("redis")
sid = bus.subscribe(["ENTRY_APPROVED"], handler, priority=10)   # lower runs first
event_id = bus.publish("ENTRY_APPROVED", {"trade_id": "..."}, source="boss")
bus.unsubscribe(sid)
```

- `MemoryBus` (default) is synchronous and in-process. Nested publishes run depth-first, so a
  replay is deterministic. A subscriber that raises is logged in `bus.errors`, and the other
  subscribers still run.
- `RedisStreamsBus` is optional (`pip install redis` and a running server). `publish` does XADD
  and `poll()` delivers. Within a batch, `FOUNDER_COMMAND` events are delivered first.
- The event types are `EventType`: the list from docs/04_MIGRATION_PLAN.md plus `MARKET_TICK`,
  `NO_ENTRY` and `ORDER_CANCELLED`.

Install (same as the other repo packages): `pip install -e packages/events`

Tests: `PYTHONPATH=packages/events/src:packages/ledger/src python -m pytest packages/events -q`
(Redis tests skip without a server).
