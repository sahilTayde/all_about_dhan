"""#55 ∪ #61: founder veto first, risk-qty stop, exit never raises on a missing row."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from brokers.factory import make_broker
from brokers.fills import ClockedPaperBroker, Quote
from contracts.clock import SimClock
from helpers import INST, NOW, make_decision, make_plan, make_router
from oms import Account, MemoryLedger, Veto, lot_size_for
from oms.router import _catastrophic_price

from control.handler import submit
from control.kinds import PAUSED
from control.store import MemoryCommandStore

NIFTY_LOT = lot_size_for(INST)

_SNAPSHOT = {
    "instrument_id": INST,
    "net_qty": NIFTY_LOT,
    "account_id": "founder",
    "avg_price": 151.40,
    "entry_order_id": "x",
    "symbol": "NIFTY 24400 CE",
}


class SpyBroker(ClockedPaperBroker):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.place_calls = 0

    def place_order(self, intent: object, decision: object) -> object:
        self.place_calls += 1
        return super().place_order(intent, decision)  # type: ignore[arg-type]


def _snapshot_exit(router: object) -> object:
    assert router._live_position(INST) is None
    return router.exit(dict(_SNAPSHOT), "FLATTEN")


def test_exit_no_store_row_flattens_without_raising_memory(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    router = make_router(tmp_path, clock, broker=spy, store=MemoryLedger())
    order = _snapshot_exit(router)
    assert not isinstance(order, Veto)
    assert spy.place_calls == 1
    assert int(order.intent.qty) == NIFTY_LOT


def test_exit_no_store_row_flattens_without_raising_sqlite(tmp_path: Path) -> None:
    from ledger.v2 import SqliteLedgerStore

    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True)
    router = make_router(tmp_path, clock, broker=spy, store=store)
    order = _snapshot_exit(router)
    assert not isinstance(order, Veto)
    assert spy.place_calls == 1
    assert int(order.intent.qty) == NIFTY_LOT
    store.close()


def test_founder_veto_blocks_entry_then_normal_stop_uses_risk_qty(tmp_path: Path) -> None:
    from control.handler import ControlHandler

    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    router = make_router(tmp_path, clock, broker=spy)
    handler = ControlHandler(
        store=MemoryCommandStore(),
        root=tmp_path,
        clock=clock,
        risk=router.risk,
        kill_switch_path=tmp_path / "data" / "ledger" / "KILL_SWITCH",
    )
    router.controls = handler

    submit(handler, "PAUSE", {"minutes": 10}, actor="sahil", reason="lunch", command_id="u-pause")
    plan, dec = make_plan(), make_decision(lots=2)
    blocked = router.submit(plan, dec, Account("founder"))
    assert isinstance(blocked, Veto)
    assert blocked.reason_code == PAUSED
    assert spy.place_calls == 0

    submit(handler, "PAUSE", {"minutes": 0}, actor="sahil", reason="resume", command_id="u-resume")
    submit(handler, "START", {}, actor="sahil", reason="go", command_id="u-start")
    dec2 = make_decision(lots=2, decision_id="dc_ok", signal_ids=["sg_ok_nifty_20260928_1002_0"])
    plan2 = make_plan(
        signal_id="sg_ok_nifty_20260928_1002_0",
        plan_id="ep_ok",
        decision_id="dc_ok",
    )
    out = router.submit(plan2, dec2, Account("founder"))
    assert not isinstance(out, Veto)
    assert spy.place_calls >= 1
    clock.advance_by(timedelta(milliseconds=250))
    router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
    )
    expected = _catastrophic_price(
        plan2, dec2, risk=router.risk, qty=max(0, int(dec2.lots) * NIFTY_LOT)
    )
    stops = [
        o
        for o in router.broker.orders.values()
        if o.intent.order_type == "SL-M" and o.is_open
    ]
    assert stops
    got = float(stops[0].trigger_price or stops[0].intent.trigger_price or 0)
    assert abs(got - expected) < 1e-9
    assert abs(float(out.intent.stop_loss or 0) - expected) < 1e-9


def test_exit_live_sqlite_position_resizes_protective_stop(tmp_path: Path) -> None:
    from ledger.v2 import SqliteLedgerStore

    clock = SimClock(NOW)
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True)
    broker = make_broker(clock=clock)
    router = make_router(tmp_path, clock, broker=broker, store=store)
    out = router.submit(make_plan(), make_decision(lots=2), Account("founder"))
    assert not isinstance(out, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
    )
    live = router._live_position(INST)
    assert live is not None
    assert int(live["net_qty"]) == 2 * NIFTY_LOT
    assert router.open_stop_qty(INST) == 2 * NIFTY_LOT

    work = dict(_SNAPSHOT)
    work["net_qty"] = NIFTY_LOT
    work["exit_price_hint"] = 155.00
    router.exit(work, "PARTIAL")
    assert router.open_stop_qty(INST) == NIFTY_LOT
    store.close()
