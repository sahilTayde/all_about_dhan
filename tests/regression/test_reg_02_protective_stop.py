"""REG-02a / REG-02e (V2-08 share): protective stop after fill; bad risk YAML allows exit."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from contracts.ids import order_id
from helpers import (
    INST,
    NOW,
    SIG,
    make_decision,
    make_plan,
    make_router,
    write_risk_cfg,
)
from oms import Account, MemoryLedger, Veto
from risk_engine import V2RiskEngine


def test_reg_02a_protective_stop_exists_after_every_entry_fill(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    broker = make_broker(clock=clock)
    router = make_router(tmp_path, clock, broker=broker)
    order = router.submit(make_plan(), make_decision(), Account("founder"))
    assert not isinstance(order, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    broker.on_depth(
        Quote(
            available_ts=clock.now(),
            bid=151.00,
            ask=151.20,
            ltp=151.10,
            instrument_id=INST,
        )
    )
    assert order.state.value == "FILLED"
    stop_id = order_id("founder", SIG, "stop")
    assert router.store.has_protective(INST)
    assert stop_id in broker.orders
    assert broker.orders[stop_id].intent.order_type == "SL-M"
    assert broker.orders[stop_id].intent.purpose == "EXIT"


def test_reg_02e_bad_risk_yaml_still_allows_exit(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    store = MemoryLedger()
    cfg = write_risk_cfg(tmp_path)
    risk = V2RiskEngine(ledger=store, config_path=cfg)
    broker = make_broker(clock=clock)
    router = make_router(tmp_path, clock, broker=broker, store=store, risk=risk)
    order = router.submit(make_plan(), make_decision(), Account("founder"))
    assert not isinstance(order, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    broker.on_depth(
        Quote(
            available_ts=clock.now(),
            bid=151.00,
            ask=151.20,
            ltp=151.10,
            instrument_id=INST,
        )
    )
    cfg.write_text("mode: [this is not: valid yaml")
    pos = store.open_positions()[0]
    pos["account_id"] = "founder"
    exited = router.exit(pos, "FOUNDER_COMMAND")
    assert exited.intent.purpose == "EXIT"
    assert risk.check_exit(exited.intent, "EXIT", now=clock.now()).approved
