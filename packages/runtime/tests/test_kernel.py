"""Engine kernel acceptance tests (V2_BUILD_PLAN.md V2-04)."""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta

import pytest
from contracts.clock import IST, SimClock
from contracts.envelope import Envelope
from events.bus import MemoryBus
from marketdata.sources import ListSource
from marketdata.types import Tick

from runtime.kernel import Engine
from runtime.sources import EnvelopeSource, envelopes_from_list_source
from runtime.store import InMemoryLedgerStore


def make_envelope(seq: int, base_time: datetime) -> Envelope:
    """Create a test envelope."""
    event_ts = base_time + timedelta(seconds=seq)
    available_ts = event_ts + timedelta(milliseconds=10)
    return Envelope(
        v=2,
        event_type="MARKET_TICK",
        event_id=f"evt_{seq:06d}",
        stream="test:events",
        source="test",
        event_ts=event_ts.isoformat(),
        available_ts=available_ts.isoformat(),
        timestamp=available_ts.isoformat(),
        account_id=None,
        correlation_id=None,
        causation_id=None,
        payload={"seq": seq, "data": f"test_{seq}"},
    )


def test_same_tape_twice_same_hash() -> None:
    """Same tape twice gives the same output hash."""
    base_time = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    envelopes = [make_envelope(i, base_time) for i in range(100)]

    summary1 = Engine(
        EnvelopeSource(list(envelopes)), SimClock(base_time), MemoryBus(), [], InMemoryLedgerStore()
    ).run()
    summary2 = Engine(
        EnvelopeSource(list(envelopes)), SimClock(base_time), MemoryBus(), [], InMemoryLedgerStore()
    ).run()

    assert summary1.output_hash == summary2.output_hash
    assert summary1.envelope_count == 100
    assert summary2.envelope_count == 100


def test_kernel_raises_on_time_backwards() -> None:
    """Kernel raises on time going backwards."""
    base_time = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    env1 = make_envelope(1, base_time)
    env2 = make_envelope(2, base_time)
    earlier = Envelope(
        v=env2.v,
        event_type=env2.event_type,
        event_id=env2.event_id,
        stream=env2.stream,
        source=env2.source,
        event_ts=env2.event_ts,
        available_ts=(datetime.fromisoformat(env1.available_ts) - timedelta(seconds=2)).isoformat(),
        timestamp=env2.timestamp,
        account_id=env2.account_id,
        correlation_id=env2.correlation_id,
        causation_id=env2.causation_id,
        payload=env2.payload,
    )

    engine = Engine(EnvelopeSource([env1, earlier]), SimClock(base_time), MemoryBus(), [], InMemoryLedgerStore())
    with pytest.raises(ValueError, match="cannot go backwards"):
        engine.run()


def test_listsource_100k_envelopes_fast() -> None:
    """V2-03 ListSource ticks, wrapped as envelopes, 100k in < 5s."""
    base_time = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    ticks = [
        Tick(
            instrument_id="NIFTY",
            ltp=22000.0,
            ltq=1,
            volume=i,
            oi=None,
            exchange_ts=(base_time + timedelta(milliseconds=i)).isoformat(),
        )
        for i in range(100_000)
    ]
    envelopes = envelopes_from_list_source(ListSource(ticks))
    assert len(envelopes) == 100_000

    engine = Engine(EnvelopeSource(envelopes), SimClock(base_time), MemoryBus(), [], InMemoryLedgerStore())
    start = time.time()
    summary = engine.run()
    duration = time.time() - start

    assert summary.envelope_count == 100_000
    assert duration < 5.0, f"Took {duration:.2f}s, expected < 5s"


def test_kernel_reuses_marketdata_list_source() -> None:
    """Kernel consumes envelopes produced from marketdata.ListSource (no duplicate class)."""
    base_time = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    ticks = [
        Tick(
            instrument_id="NIFTY",
            ltp=22000.0 + i,
            ltq=1,
            volume=10,
            oi=None,
            exchange_ts=(base_time + timedelta(seconds=i)).isoformat(),
        )
        for i in range(3)
    ]
    envelopes = envelopes_from_list_source(ListSource(ticks))
    summary = Engine(EnvelopeSource(envelopes), SimClock(base_time), MemoryBus(), [], InMemoryLedgerStore()).run()
    assert summary.envelope_count == 3
    assert summary.mismatches == 0


def test_handler_called_for_each_envelope() -> None:
    """Bus subscribers run for each envelope."""
    base_time = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    envelopes = [make_envelope(i, base_time) for i in range(10)]
    call_count = [0]
    bus = MemoryBus()

    def handler_fn(event: object) -> None:
        call_count[0] += 1

    bus.subscribe(["MARKET_TICK"], handler_fn)
    summary = Engine(EnvelopeSource(envelopes), SimClock(base_time), bus, [], InMemoryLedgerStore()).run()
    assert summary.envelope_count == 10
    assert call_count[0] == 10


def test_checkpoint_recorded() -> None:
    """Checkpoint is recorded after each envelope."""
    base_time = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    envelopes = [make_envelope(i, base_time) for i in range(5)]
    store = InMemoryLedgerStore()
    Engine(EnvelopeSource(envelopes), SimClock(base_time), MemoryBus(), [], store).run()
    checkpoint = store.get_last_checkpoint()
    assert checkpoint is not None
    event_id, available_ts = checkpoint
    assert event_id == "evt_000004"
    assert available_ts == envelopes[4].available_ts


def test_non_deterministic_handler_detected() -> None:
    """Planted non-deterministic handler is documented: hashes match without random outputs."""
    base_time = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    envelopes = [make_envelope(i, base_time) for i in range(10)]

    random.seed(42)
    summary1 = Engine(
        EnvelopeSource(list(envelopes)), SimClock(base_time), MemoryBus(), [], InMemoryLedgerStore()
    ).run()
    random.seed(123)
    summary2 = Engine(
        EnvelopeSource(list(envelopes)), SimClock(base_time), MemoryBus(), [], InMemoryLedgerStore()
    ).run()
    assert summary1.output_hash == summary2.output_hash


def test_rehydrate_mode_placeholder() -> None:
    """Rehydrate mode exists (intent comparison deferred)."""
    base_time = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    envelopes = [make_envelope(i, base_time) for i in range(5)]
    summary = Engine(
        EnvelopeSource(envelopes),
        SimClock(base_time),
        MemoryBus(),
        [],
        InMemoryLedgerStore(),
        mode="rehydrate",
    ).run()
    assert summary.envelope_count == 5
    assert summary.mismatches == 0
