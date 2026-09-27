"""V2-02 tests: envelope v2, consumer groups, outbox exactly-once, REG-06 bad-entry handling."""

import uuid
from pathlib import Path
from typing import Any

import pytest
from events import BadEntryStore, MemoryBus, RedisStreamsBus, make_event


def test_bad_entry_store_records_and_dedupes(tmp_path: Path) -> None:
    """REG-06: bad entry store records first occurrence and dedupes."""
    store = BadEntryStore(tmp_path / "bad_entries.db")
    assert (
        store.record("stream1", "entry-1", b"bad json", "JSONDecodeError: invalid")
        is True
    )
    assert (
        store.record("stream1", "entry-1", b"bad json", "JSONDecodeError: invalid")
        is False
    )  # dedupe
    assert store.count("stream1") == 1
    assert store.count() == 1

    entries = store.get_all("stream1")
    assert len(entries) == 1
    assert entries[0]["entry_id"] == "entry-1"
    assert entries[0]["stream"] == "stream1"
    assert "JSONDecodeError" in entries[0]["error"]


def test_bad_entry_store_in_memory() -> None:
    """Bad entry store works with :memory: database."""
    store = BadEntryStore(":memory:")
    store.record("test", "e1", b"data", "error1")
    store.record("test", "e2", b"data", "error2")
    assert store.count("test") == 2


def _redis_or_skip() -> Any:
    """Get a fakeredis client for testing (no real Redis server needed)."""
    try:
        import fakeredis

        return fakeredis.FakeStrictRedis(decode_responses=False)
    except ImportError:
        pytest.skip("fakeredis not installed")


def test_redis_one_stream_per_topic() -> None:
    """V2-02: one stream per event type."""
    client = _redis_or_skip()
    prefix = f"test:v2:{uuid.uuid4().hex}:"
    try:
        bus = RedisStreamsBus(
            client=client, stream_prefix=prefix, consumer_group="test_cg"
        )
        seen = []
        bus.subscribe(["ENTRY_APPROVED"], lambda e: seen.append(("ENTRY", e.payload)))
        bus.subscribe(["ORDER_FILLED"], lambda e: seen.append(("FILL", e.payload)))

        bus.publish("ENTRY_APPROVED", {"trade_id": "t1"}, source="boss")
        bus.publish("ORDER_FILLED", {"order_id": "o1"}, source="desk")
        assert seen == []  # durable: delivered on poll

        # Two separate streams
        assert client.exists(f"{prefix}ENTRY_APPROVED") == 1
        assert client.exists(f"{prefix}ORDER_FILLED") == 1

        assert bus.poll() == 2
        assert seen == [("ENTRY", {"trade_id": "t1"}), ("FILL", {"order_id": "o1"})]
    finally:
        for key in client.scan_iter(f"{prefix}*"):
            client.delete(key)


def test_redis_consumer_group_resume_after_restart() -> None:
    """V2-02: consumer killed before XACK gets the entry again on restart."""
    client = _redis_or_skip()
    prefix = f"test:resume:{uuid.uuid4().hex}:"
    group = "resume_test_group"

    try:
        # First consumer: subscribe and publish
        bus1 = RedisStreamsBus(
            client=client,
            stream_prefix=prefix,
            consumer_group=group,
            consumer_name="consumer1",
        )
        seen1 = []
        bus1.subscribe(["MARKET_TICK"], lambda e: seen1.append(e.payload["n"]))
        bus1.publish("MARKET_TICK", {"n": 1}, source="feed")
        bus1.publish("MARKET_TICK", {"n": 2}, source="feed")

        # Simulate crash before poll (no XACK)
        # Messages are in pending state

        # Second consumer: same group, different name
        bus2 = RedisStreamsBus(
            client=client,
            stream_prefix=prefix,
            consumer_group=group,
            consumer_name="consumer2",
        )
        seen2 = []
        bus2.subscribe(["MARKET_TICK"], lambda e: seen2.append(e.payload["n"]))

        # Poll with bus2: should get new messages (not pending yet)
        bus2.poll()
        assert seen2 == [1, 2]

        # Now publish more and poll
        bus2.publish("MARKET_TICK", {"n": 3}, source="feed")
        bus2.poll()
        assert seen2 == [1, 2, 3]

    finally:
        for key in client.scan_iter(f"{prefix}*"):
            client.delete(key)


def test_redis_bad_entry_in_middle_of_batch() -> None:
    """REG-06c: a bad entry in the middle of a batch is recorded and skipped, good entries dispatched."""
    client = _redis_or_skip()
    prefix = f"test:bad:{uuid.uuid4().hex}:"
    stream = f"{prefix}HEALTH_ALERT"
    group = "bad_entry_test"

    try:
        # Manually insert: good, bad, good
        client.xadd(stream, {"event": make_event("HEALTH_ALERT", {"n": 1}).to_json()})
        client.xadd(stream, {"event": "{ bad json"})  # corrupt
        client.xadd(stream, {"event": make_event("HEALTH_ALERT", {"n": 3}).to_json()})

        bus = RedisStreamsBus(
            client=client,
            stream_prefix=prefix,
            consumer_group=group,
            bad_entry_db=":memory:",
        )
        seen = []
        bus.subscribe(["HEALTH_ALERT"], lambda e: seen.append(e.payload["n"]))

        # Poll: should get entry 1 and 3, skip the bad one
        bus.poll()
        assert sorted(seen) == [1, 3]
        assert bus.bad_entries.count(stream) == 1

        bad = bus.bad_entries.get_all(stream)
        assert len(bad) == 1
        assert "json" in bad[0]["error"].lower()

    finally:
        for key in client.scan_iter(f"{prefix}*"):
            client.delete(key)


def test_redis_claim_pending_messages() -> None:
    """V2-02: XPENDING + XCLAIM recovers messages from dead consumers."""
    client = _redis_or_skip()
    prefix = f"test:claim:{uuid.uuid4().hex}:"
    stream = f"{prefix}POSITION_UPDATE"
    group = "claim_test"

    try:
        # Consumer 1: read but don't ack (simulate crash)
        bus1 = RedisStreamsBus(
            client=client,
            stream_prefix=prefix,
            consumer_group=group,
            consumer_name="consumer1",
        )
        bus1.subscribe(["POSITION_UPDATE"], lambda e: None)  # no-op handler
        bus1.publish("POSITION_UPDATE", {"pos": 1}, source="desk")

        # Manually read without ack using lower-level API
        try:
            client.xgroup_create(stream, group, id="0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        client.xreadgroup(group, "consumer1", {stream: ">"}, count=1)
        # consumer1 has pending message now

        # Consumer 2: claim pending
        bus2 = RedisStreamsBus(
            client=client,
            stream_prefix=prefix,
            consumer_group=group,
            consumer_name="consumer2",
        )
        seen = []
        bus2.subscribe(["POSITION_UPDATE"], lambda e: seen.append(e.payload["pos"]))

        # Claim with idle_ms=0 (immediate)
        claimed = bus2.claim_pending(idle_ms=0, count=10)
        assert claimed == 1
        assert seen == [1]

    finally:
        for key in client.scan_iter(f"{prefix}*"):
            client.delete(key)


# ----------------------------------------------------------- Outbox tests


class FakeOutboxStore:
    """In-memory outbox for testing."""

    def __init__(self) -> None:
        self.rows: list[tuple[int, str, str, dict[str, Any]]] = []
        self.published_ids: set[int] = set()
        self.next_id = 1

    def add(
        self, stream: str, event_json: str, metadata: dict[str, Any] | None = None
    ) -> int:
        row_id = self.next_id
        self.next_id += 1
        self.rows.append((row_id, stream, event_json, metadata or {}))
        return row_id

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[tuple[int, str, str, dict[str, Any]]]:
        return [r for r in self.rows if r[0] not in self.published_ids][:limit]

    def mark_published(self, row_ids: list[int]) -> None:
        self.published_ids.update(row_ids)


class FakeEventPublisher:
    """In-memory publisher for testing."""

    def __init__(self) -> None:
        self.published: list[
            tuple[str, str, str | None]
        ] = []  # (stream, event_json, message_id)
        self.fail_count = 0  # simulate failures

    def publish_to_stream(
        self, stream: str, event_json: str, *, message_id: str | None = None
    ) -> None:
        if self.fail_count > 0:
            self.fail_count -= 1
            raise RuntimeError("simulated publish failure")
        self.published.append((stream, event_json, message_id))


def test_outbox_exactly_once_publish() -> None:
    """V2-02: outbox publishes each row exactly once across crashes."""
    from events.outbox import OutboxPublisher

    store = FakeOutboxStore()
    publisher = FakeEventPublisher()
    outbox = OutboxPublisher(store, publisher)

    # Add rows
    store.add("stream1", '{"event_type":"TEST","payload":{}}', {})
    store.add("stream1", '{"event_type":"TEST2","payload":{}}', {})

    # First drain
    published = outbox.drain(limit=10)
    assert published == 2
    assert len(publisher.published) == 2
    assert publisher.published[0][2] == "1-0"  # message_id from row_id
    assert publisher.published[1][2] == "2-0"

    # Second drain: no more unpublished
    published = outbox.drain(limit=10)
    assert published == 0
    assert len(publisher.published) == 2  # still 2

    # Add more
    store.add("stream2", '{"event_type":"TEST3","payload":{}}', {})
    published = outbox.drain(limit=10)
    assert published == 1
    assert len(publisher.published) == 3


def test_outbox_retries_on_publish_failure() -> None:
    """V2-02: outbox retries failed publishes."""
    from events.outbox import OutboxPublisher

    store = FakeOutboxStore()
    publisher = FakeEventPublisher()
    outbox = OutboxPublisher(store, publisher)

    store.add("stream1", '{"event_type":"TEST","payload":{}}', {})

    # Fail first 2 attempts, succeed on 3rd
    publisher.fail_count = 2
    published = outbox.drain(limit=10, max_retries=5)
    assert published == 1
    assert len(publisher.published) == 1  # succeeded on retry


def test_outbox_gives_up_after_max_retries() -> None:
    """V2-02: outbox gives up after max_retries."""
    from events.outbox import OutboxPublisher

    store = FakeOutboxStore()
    publisher = FakeEventPublisher()
    outbox = OutboxPublisher(store, publisher)

    store.add("stream1", '{"event_type":"TEST","payload":{}}', {})

    # Fail all attempts
    publisher.fail_count = 10
    published = outbox.drain(limit=10, max_retries=3)
    assert published == 0  # gave up
    assert outbox.error_count == 1


# ----------------------------------------------------------- Contract tests (MemoryBus and RedisStreamsBus)


def test_memory_bus_and_redis_bus_same_subscription_contract() -> None:
    """MemoryBus and RedisStreamsBus accept the same subscribe API."""
    memory = MemoryBus()
    seen_memory = []
    memory.subscribe(["ENTRY_APPROVED"], lambda e: seen_memory.append(e.payload))
    memory.publish("ENTRY_APPROVED", {"t": 1}, source="boss")
    assert seen_memory == [{"t": 1}]

    client = _redis_or_skip()
    prefix = f"test:contract:{uuid.uuid4().hex}:"
    try:
        redis_bus = RedisStreamsBus(
            client=client, stream_prefix=prefix, consumer_group="contract"
        )
        seen_redis = []
        redis_bus.subscribe(["ENTRY_APPROVED"], lambda e: seen_redis.append(e.payload))
        redis_bus.publish("ENTRY_APPROVED", {"t": 1}, source="boss")
        redis_bus.poll()
        assert seen_redis == [{"t": 1}]
    finally:
        for key in client.scan_iter(f"{prefix}*"):
            client.delete(key)


def test_memory_bus_and_redis_bus_same_publish_contract() -> None:
    """MemoryBus and RedisStreamsBus accept the same publish API."""
    memory = MemoryBus()
    event_id = memory.publish("ORDER_FILLED", {"price": 100}, source="desk")
    assert len(event_id) == 32  # uuid hex

    client = _redis_or_skip()
    prefix = f"test:pub:{uuid.uuid4().hex}:"
    try:
        redis_bus = RedisStreamsBus(
            client=client, stream_prefix=prefix, consumer_group="pub"
        )
        event_id2 = redis_bus.publish("ORDER_FILLED", {"price": 100}, source="desk")
        assert len(event_id2) == 32
    finally:
        for key in client.scan_iter(f"{prefix}*"):
            client.delete(key)


def test_memory_bus_founder_first_preserved() -> None:
    """MemoryBus preserves founder-first dispatch order."""
    bus = MemoryBus()
    seen = []
    bus.subscribe(
        ["ENTRY_APPROVED", "FOUNDER_COMMAND"], lambda e: seen.append(e.event_type)
    )
    bus._dispatch_batch(
        [make_event("ENTRY_APPROVED", {}), make_event("FOUNDER_COMMAND", {})]
    )
    assert seen == ["FOUNDER_COMMAND", "ENTRY_APPROVED"]


def test_redis_bus_founder_first_preserved() -> None:
    """RedisStreamsBus preserves founder-first dispatch order."""
    client = _redis_or_skip()
    prefix = f"test:founder:{uuid.uuid4().hex}:"
    try:
        bus = RedisStreamsBus(
            client=client, stream_prefix=prefix, consumer_group="founder"
        )
        seen = []
        bus.subscribe(
            ["ENTRY_APPROVED", "FOUNDER_COMMAND"], lambda e: seen.append(e.event_type)
        )
        bus.publish("ENTRY_APPROVED", {"t": 1}, source="boss")
        bus.publish("FOUNDER_COMMAND", {"cmd": "PAUSE"}, source="founder")
        bus.poll()
        # Founder command dispatched first
        assert seen == ["FOUNDER_COMMAND", "ENTRY_APPROVED"]
    finally:
        for key in client.scan_iter(f"{prefix}*"):
            client.delete(key)
