"""Exchange lot size is the only lot size the router may send."""

from __future__ import annotations

from typing import Any

import pytest
from brokers.fills import ClockedPaperBroker
from contracts.clock import SimClock
from contracts.ids import order_id
from helpers import INST, NOW, SIG, make_decision, make_plan, make_router

from oms import Account, Veto, lot_size_for
from oms.router import OrderRouter

NIFTY_LOT = lot_size_for(INST)


class SpyBroker(ClockedPaperBroker):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.place_calls = 0
        self.last_intent: Any = None

    def place_order(self, intent: object, decision: object) -> object:
        self.place_calls += 1
        self.last_intent = intent
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


class PoisonedLotRouter(OrderRouter):
    """Forces a non-exchange lot_size onto the intent after mismatch checks."""

    def _intent(self, **kw: Any) -> Any:  # type: ignore[override]
        kw["lot_size"] = 10
        return super()._intent(**kw)


def test_lot_size_mismatch_vetoed_nothing_sent(tmp_path: object) -> None:
    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    router = make_router(tmp_path, clock, broker=spy)  # type: ignore[arg-type]
    out = router.submit(
        make_plan(),
        make_decision(lots=1, lot_size=10),
        Account("founder"),
    )
    assert isinstance(out, Veto)
    assert out.reason_code == "LOT_SIZE_MISMATCH"
    assert spy.place_calls == 0
    assert router.store.get_order(out.client_order_id) is None


def test_send_time_qty_must_be_whole_lots(tmp_path: object) -> None:
    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    base = make_router(tmp_path, clock, broker=spy)  # type: ignore[arg-type]
    router = PoisonedLotRouter(
        clock=clock,
        risk=base.risk,
        broker=spy,
        store=base.store,
        bus=base.bus,
    )
    out = router.submit(make_plan(), make_decision(lots=1, lot_size=None), Account("founder"))
    assert isinstance(out, Veto)
    assert out.reason_code == "QTY_NOT_WHOLE_LOT"
    assert spy.place_calls == 0


def test_rebuild_refuses_wrong_lot_size(tmp_path: object) -> None:
    clock = SimClock(NOW)
    broker = TimeoutOnce(clock=clock)
    router = make_router(tmp_path, clock, broker=broker)  # type: ignore[arg-type]
    plan, dec, acc = make_plan(), make_decision(lots=1, lot_size=NIFTY_LOT), Account("founder")
    with pytest.raises(TimeoutError):
        router.submit(plan, dec, acc)
    oid = order_id("founder", SIG, "entry")
    row = router.store.get_order(oid)
    assert row is not None and row["needs_lookup"] is True
    row["lot_size"] = 10
    out = router.submit(plan, dec, acc)
    assert isinstance(out, Veto)
    assert out.reason_code == "LOT_SIZE_MISMATCH"
    assert broker.attempts == 1


def test_flatten_never_exceeds_net_qty(tmp_path: object) -> None:
    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    router = make_router(tmp_path, clock, broker=spy)  # type: ignore[arg-type]
    pos = {
        "instrument_id": INST,
        "net_qty": 70,
        "account_id": "founder",
        "avg_price": 151.40,
        "entry_order_id": "x",
    }
    alerts: list[str] = []
    router.bus.subscribe(["HEALTH_ALERT"], lambda e: alerts.append(e.event_type))
    order = router.exit(pos, "FLATTEN")
    assert spy.place_calls == 1
    assert int(spy.last_intent.qty) == NIFTY_LOT
    assert int(spy.last_intent.qty) <= 70
    assert int(order.intent.qty) <= int(pos["net_qty"])
    assert alerts == ["HEALTH_ALERT"]

    spy.place_calls = 0
    with pytest.raises(ValueError, match="whole lot"):
        router.exit({**pos, "net_qty": 10}, "FLATTEN")
    assert spy.place_calls == 0
