"""V2-14: a failing or slow alert sink must not stall the event bus."""

from __future__ import annotations

import time
from datetime import datetime

from contracts.clock import IST, SimClock
from events.bus import MemoryBus
from health.v2_alerts import Alert
from health.v2_monitor import V2HealthMonitor

MON = datetime(2026, 9, 28, 10, 30, tzinfo=IST)

_POS = {
    "position_id": "ps_bare",
    "account_id": "founder",
    "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24400:CE",
    "net_qty": 65,
    "avg_price": 100.0,
    "mark": 101.0,
    "unrealized_inr": 65.0,
    "stop": {},
    "protective_order": None,
    "strategy_id": "TEST",
}


class SlowSink:
    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.seen = 0

    def emit(self, alert: Alert) -> None:
        time.sleep(self.delay)
        self.seen += 1


class BoomSink:
    def emit(self, alert: Alert) -> None:
        raise OSError("telegram down")


def test_slow_alert_sink_does_not_stall_bus(tmp_path: object) -> None:
    from pathlib import Path

    bus = MemoryBus()
    traded: list[str] = []
    bus.subscribe(["POSITION_UPDATE"], lambda e: traded.append(e.event_id), priority=90)
    sink = SlowSink(1.5)
    mon = V2HealthMonitor(
        clock=SimClock(MON),
        sink=sink,
        queue_sink=True,
        state_path=Path(str(tmp_path)) / "d.json",
        evaluate_on_event=True,
    )
    mon.attach_bus(bus)
    t0 = time.perf_counter()
    bus.publish("POSITION_UPDATE", _POS, source="engine")
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.25, f"bus stalled for {elapsed:.3f}s"
    assert traded, "trading subscriber must still run"
    assert bus.errors == []
    mon.flush(timeout=3.0)
    assert sink.seen >= 1


def test_failing_alert_sink_does_not_stall_bus_or_raise(tmp_path: object) -> None:
    from pathlib import Path

    bus = MemoryBus()
    traded: list[int] = []
    bus.subscribe(["POSITION_UPDATE"], lambda e: traded.append(1), priority=90)
    mon = V2HealthMonitor(
        clock=SimClock(MON),
        sink=BoomSink(),
        queue_sink=True,
        state_path=Path(str(tmp_path)) / "d.json",
        evaluate_on_event=True,
    )
    mon.attach_bus(bus)
    t0 = time.perf_counter()
    bus.publish("POSITION_UPDATE", _POS, source="engine")
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.25, f"bus stalled for {elapsed:.3f}s"
    assert traded == [1]
    assert bus.errors == []
    mon.flush(timeout=1.0)
