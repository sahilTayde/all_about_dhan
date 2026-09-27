"""REG-03a/b/c: forced close exits the held instrument and qty after spot moves 3 strikes."""

from __future__ import annotations

from datetime import datetime, timedelta

from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from helpers import INST, NOW, envelope, make_decision, make_exit_plan, make_manager, make_plan
from oms import Account, Veto
from oms.positions import exit_from_held
from risk_engine import IST

MOVED = "NSE_FNO:NIFTY:2026-09-29:24550:CE"  # +3 NIFTY strikes


def _open(tmp_path, clock):
    broker = make_broker(clock=clock)
    pm = make_manager(tmp_path, clock, broker=broker)
    order = pm.router.submit(
        make_plan(), make_decision(lots=2), Account("founder"), exit_plan=make_exit_plan()
    )
    assert not isinstance(order, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
    )
    # spot (quotes) move three strikes away; book must stay on the held contract
    clock.advance_by(timedelta(seconds=5))
    pm.on_market(
        envelope("DEPTH_QUOTE", clock.now(), {"instrument_id": MOVED, "bid": 80.0, "ask": 80.2, "ltp": 80.1})
    )
    pos = pm.open_book()[0]
    assert pos["instrument_id"] == INST
    assert pos["net_qty"] == 130
    return pm, pos


def _assert_held(pm, pos, reason: str) -> None:
    intent = exit_from_held(pos, reason)
    assert intent.instrument_id == INST
    assert intent.qty == 130
    assert pm.store.closed[-1]["instrument_id"] == INST
    assert pm.store.closed[-1]["last_exit_qty"] == 130
    assert not pm.open_book()


def test_reg_03a_eod_exits_held_instrument(tmp_path) -> None:
    clock = SimClock(NOW)
    pm, pos = _open(tmp_path, clock)
    clock.advance_to(datetime(2026, 9, 28, 15, 15, tzinfo=IST))
    pm.on_market(envelope("CLOCK", clock.now(), {"minute": "15:15"}))
    _assert_held(pm, pos, "FLATTEN_EOD")


def test_reg_03b_founder_exits_held_instrument(tmp_path) -> None:
    clock = SimClock(NOW)
    pm, pos = _open(tmp_path, clock)
    clock.advance_by(timedelta(minutes=2))
    pm.on_market(envelope("FOUNDER_COMMAND", clock.now(), {"kind": "CUT_LOSS", "instrument_id": INST}))
    _assert_held(pm, pos, "FOUNDER_COMMAND")


def test_reg_03c_kill_switch_exits_held_instrument(tmp_path) -> None:
    clock = SimClock(NOW)
    pm, pos = _open(tmp_path, clock)
    pm.kill_switch = True
    clock.advance_by(timedelta(seconds=1))
    pm.on_market(envelope("CLOCK", clock.now(), {"minute": "10:02"}))
    _assert_held(pm, pos, "KILL_SWITCH")
