"""V2-08 router: idempotent submit, risk-before-broker, clocked decision age, adopt."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from brokers.factory import make_broker
from brokers.fills import ClockedPaperBroker, Quote
from contracts.clock import SimClock
from contracts.ids import order_id
from events.bus import MemoryBus
from helpers import INST, NOW, SIG, make_decision, make_plan, make_router, write_risk_cfg
from risk_engine import IST, V2RiskEngine

from oms import Account, MemoryLedger, Veto


class SpyBroker(ClockedPaperBroker):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.place_calls = 0

    def place_order(self, intent: object, decision: object) -> object:
        self.place_calls += 1
        return super().place_order(intent, decision)  # type: ignore[arg-type]


class TimeoutOnce(ClockedPaperBroker):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.attempts = 0

    def place_order(self, intent: object, decision: object) -> object:
        self.attempts += 1
        if self.attempts == 1:
            raise TimeoutError("no broker response")
        return super().place_order(intent, decision)  # type: ignore[arg-type]


def test_same_decision_routed_twice_yields_one_order(tmp_path: object) -> None:
    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    router = make_router(tmp_path, clock, broker=spy)  # type: ignore[arg-type]
    plan, dec, acc = make_plan(), make_decision(), Account("founder")
    a = router.submit(plan, dec, acc)
    b = router.submit(plan, dec, acc)
    assert not isinstance(a, Veto) and not isinstance(b, Veto)
    assert a.client_order_id == b.client_order_id == order_id("founder", SIG, "entry")
    assert len(a.client_order_id) == 27
    assert spy.place_calls == 1


def test_risk_veto_never_reaches_broker(tmp_path: object) -> None:
    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    bus = MemoryBus()
    seen: list[str] = []
    bus.subscribe(["ENTRY_VETOED"], lambda e: seen.append(e.event_type))
    store = MemoryLedger()
    cfg = write_risk_cfg(tmp_path, kill_switch=True)  # type: ignore[arg-type]
    risk = V2RiskEngine(ledger=store, config_path=cfg, bus=bus)
    router = make_router(tmp_path, clock, broker=spy, store=store, bus=bus, risk=risk)  # type: ignore[arg-type]
    out = router.submit(make_plan(), make_decision(), Account("founder"))
    assert isinstance(out, Veto)
    assert out.reason_code == "KILL_SWITCH"
    assert spy.place_calls == 0
    assert seen == ["ENTRY_VETOED"]
    assert store.get_order(out.client_order_id) is None


def test_decision_age_uses_engine_clock_not_wall(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = SimClock(NOW)
    far = datetime(2099, 1, 1, 12, 0, tzinfo=IST)

    class _Far:
        @staticmethod
        def now(tz: object = None) -> datetime:
            return far

    monkeypatch.setattr("brokers.orders.datetime", _Far)
    router = make_router(tmp_path, clock)  # type: ignore[arg-type]
    out = router.submit(make_plan(), make_decision(), Account("founder"))
    assert not isinstance(out, Veto)
    assert out.state.value == "SUBMITTED"


def test_needs_lookup_adopt_before_resend(tmp_path: object) -> None:
    clock = SimClock(NOW)
    broker = TimeoutOnce(clock=clock)
    router = make_router(tmp_path, clock, broker=broker)  # type: ignore[arg-type]
    plan, dec, acc = make_plan(), make_decision(), Account("founder")
    with pytest.raises(TimeoutError):
        router.submit(plan, dec, acc)
    row = router.store.get_order(order_id("founder", SIG, "entry"))
    assert row is not None and row["needs_lookup"] is True
    out = router.submit(plan, dec, acc)
    assert not isinstance(out, Veto)
    assert broker.attempts == 2
    assert router.store.get_order(out.client_order_id)["needs_lookup"] is False


def test_depth_fill_then_protective_stop(tmp_path: object) -> None:
    clock = SimClock(NOW)
    broker = make_broker(clock=clock)
    router = make_router(tmp_path, clock, broker=broker)  # type: ignore[arg-type]
    order = router.submit(make_plan(), make_decision(), Account("founder"))
    assert not isinstance(order, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
    )
    assert order.state.value == "FILLED"
    assert order.avg_fill_price == 151.40  # limit, no price improvement
    assert broker.fill_models[order.client_order_id] == "depth"
    key = INST
    assert router.store.has_protective(key)
    stop_id = order_id("founder", SIG, "stop")
    assert stop_id in broker.orders
    assert broker.orders[stop_id].intent.order_type == "SL-M"
