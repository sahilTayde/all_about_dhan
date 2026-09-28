"""Event bus: schema, subscribe/priority, crash isolation, audit log, founder-first, Redis (skip if absent)."""

import json
import sqlite3
import time
import uuid

import pytest

from events import Event, EventAuditLog, EventType, MemoryBus, RedisStreamsBus, create_bus, make_event


def test_plan_event_types_exist():
    for name in ("PRE_MARKET_SUMMARY", "REQUEST_VOTES", "ANALYST_VOTE", "ENTRY_APPROVED", "EXIT_APPROVED",
                 "ORDER_SUBMITTED", "ORDER_FILLED", "POSITION_UPDATE", "POSITION_CLOSED", "ENTRY_VETOED",
                 "HEALTH_ALERT", "FOUNDER_COMMAND"):
        assert EventType(name).value == name
    for name in ("DECISION", "ADVICE"):
        assert EventType(name).value == name


def test_event_json_round_trip_and_validation():
    e = make_event(EventType.ENTRY_APPROVED, {"trade_id": "t1", "lots": 25}, source="boss")
    back = Event.from_json(e.to_json())
    assert back == e and set(json.loads(e.to_json())) == {"event_type", "event_id", "timestamp", "source", "payload"}
    with pytest.raises(ValueError):
        make_event("NOT_A_TYPE", {})
    with pytest.raises(TypeError):
        make_event("ENTRY_APPROVED", ["not", "a", "dict"])
    with pytest.raises(TypeError):
        MemoryBus().publish("ENTRY_APPROVED", {"obj": object()})


def test_publish_subscribe_unsubscribe_and_priority():
    bus, seen = MemoryBus(), []
    bus.subscribe(["MARKET_TICK"], lambda e: seen.append("boss"), priority=20)
    sid = bus.subscribe(["MARKET_TICK", "FOUNDER_COMMAND"], lambda e: seen.append("desk"), priority=10)
    bus.subscribe(["ENTRY_APPROVED"], lambda e: seen.append("other"))
    event_id = bus.publish("MARKET_TICK", {"i": 1}, source="feed")
    assert seen == ["desk", "boss"] and len(event_id) == 32
    assert bus.unsubscribe(sid) and not bus.unsubscribe(sid)
    bus.publish("MARKET_TICK", {"i": 2})
    assert seen == ["desk", "boss", "boss"]


def test_nested_publish_is_depth_first():
    bus, order = MemoryBus(), []

    def boss(e):
        order.append("boss:start")
        bus.publish("ENTRY_APPROVED", {"t": 1}, source="boss")
        order.append("boss:end")

    bus.subscribe(["MARKET_TICK"], boss)
    bus.subscribe(["ENTRY_APPROVED"], lambda e: order.append("desk:book"))
    bus.publish("MARKET_TICK", {})
    assert order == ["boss:start", "desk:book", "boss:end"]


def test_crashing_subscriber_does_not_stop_others():
    bus, seen = MemoryBus(), []
    bus.subscribe(["HEALTH_ALERT"], lambda e: 1 / 0, priority=1)
    bus.subscribe(["HEALTH_ALERT"], lambda e: seen.append(e.payload["n"]), priority=2)
    bus.publish("HEALTH_ALERT", {"n": 7})
    assert seen == [7]
    assert bus.errors and bus.errors[0]["error"].startswith("ZeroDivisionError")
    strict = MemoryBus(raise_errors=True)
    strict.subscribe(["HEALTH_ALERT"], lambda e: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        strict.publish("HEALTH_ALERT", {})


def test_every_event_is_audited_before_delivery_and_log_is_append_only(tmp_path):
    audit = EventAuditLog(tmp_path / "events.sqlite")
    bus = MemoryBus(audit)
    counts_at_delivery = []
    bus.subscribe(["ORDER_FILLED"], lambda e: counts_at_delivery.append(audit.count()))
    bus.publish("ORDER_FILLED", {"price": 101.5}, source="desk")
    bus.publish("POSITION_CLOSED", {"pnl": -3.2}, source="desk")
    assert counts_at_delivery == [1]
    assert audit.counts() == {"ORDER_FILLED": 1, "POSITION_CLOSED": 1}
    row = audit.rows("ORDER_FILLED")[0]
    assert row["source"] == "desk" and row["payload"] == {"price": 101.5}
    for sql in ("DELETE FROM events", "UPDATE events SET source = 'x'"):
        with pytest.raises(sqlite3.DatabaseError):
            with audit.conn:
                audit.conn.execute(sql)


def test_audit_can_share_the_ledger_connection():
    from ledger import Ledger

    led = Ledger(":memory:")
    bus = MemoryBus(EventAuditLog(led.conn))
    bus.publish("HEALTH_ALERT", {"service": "x"})
    assert led.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert led.trades() == []


def test_batch_dispatch_puts_founder_first():
    bus, seen = MemoryBus(), []
    bus.subscribe(["ENTRY_APPROVED", "FOUNDER_COMMAND", "MARKET_TICK"], lambda e: seen.append(e.event_type))
    bus._dispatch_batch([make_event("ENTRY_APPROVED", {}), make_event("MARKET_TICK", {}),
                         make_event("FOUNDER_COMMAND", {"command": "PAUSE_ENTRIES"})])
    assert seen == ["FOUNDER_COMMAND", "ENTRY_APPROVED", "MARKET_TICK"]


def test_create_bus_backends(monkeypatch):
    assert create_bus().backend == "memory"
    monkeypatch.setenv("USE_EVENT_BUS_BACKEND", "memory")
    assert isinstance(create_bus(), MemoryBus)
    with pytest.raises(ValueError):
        create_bus("kafka")


def test_publish_latency_budget(tmp_path):
    """docs/04_MIGRATION_PLAN.md: publish < 5 ms p99 (audit on an on-disk SQLite file, one subscriber)."""
    bus = MemoryBus(EventAuditLog(tmp_path / "bench.sqlite"))
    bus.subscribe(["ANALYST_VOTE"], lambda e: None)
    lat = []
    for n in range(2000):
        t0 = time.perf_counter()
        bus.publish("ANALYST_VOTE", {"request_id": "r", "analyst_id": f"A{n % 22}", "signal": "HOLD",
                                     "confidence": 0.0, "reasoning": "bench", "metadata": {"n": n}})
        lat.append((time.perf_counter() - t0) * 1000)
    lat.sort()
    p99 = lat[int(0.99 * len(lat)) - 1]
    print(f"publish p50 {lat[len(lat) // 2]:.3f} ms p99 {p99:.3f} ms")
    assert p99 < 5.0


# ----------------------------------------------------------- Redis Streams


def _redis_or_skip():
    try:
        import fakeredis
        return fakeredis.FakeStrictRedis(decode_responses=False)
    except ImportError:
        pytest.skip("fakeredis not installed")


def test_redis_streams_round_trip_and_founder_first():
    client = _redis_or_skip()
    stream = f"test:events:{uuid.uuid4().hex}"
    try:
        audit = EventAuditLog()
        bus = RedisStreamsBus(client=client, stream=stream, audit=audit)
        seen = []
        bus.subscribe(["ENTRY_APPROVED", "FOUNDER_COMMAND"], lambda e: seen.append((e.event_type, e.payload)))
        bus.publish("ENTRY_APPROVED", {"trade_id": "t1"}, source="boss")
        bus.publish("FOUNDER_COMMAND", {"command": "PAUSE_ENTRIES"}, source="founder")
        assert seen == []  # durable transport: delivered on poll
        assert bus.poll() == 2
        assert seen == [("FOUNDER_COMMAND", {"command": "PAUSE_ENTRIES"}), ("ENTRY_APPROVED", {"trade_id": "t1"})]
        assert bus.poll() == 0 and audit.count() == 2
        replay = RedisStreamsBus(client=client, stream=stream, start_id="0-0")
        got = []
        replay.subscribe(["ENTRY_APPROVED"], lambda e: got.append(e.payload["trade_id"]))
        replay.poll()
        assert got == ["t1"]
    finally:
        client.delete(stream)


def test_redis_publish_latency_budget():
    client = _redis_or_skip()
    stream = f"test:bench:{uuid.uuid4().hex}"
    try:
        bus = RedisStreamsBus(client=client, stream=stream)
        lat = []
        for n in range(1000):
            t0 = time.perf_counter()
            bus.publish("ANALYST_VOTE", {"n": n})
            lat.append((time.perf_counter() - t0) * 1000)
        lat.sort()
        assert lat[int(0.99 * len(lat)) - 1] < 5.0
    finally:
        client.delete(stream)
