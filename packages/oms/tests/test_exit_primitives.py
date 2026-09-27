"""V2-09b primitive table: structural, ATR (fixed at fill), signal-flip."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from contracts.payloads import AtrStop, Level, SignalFlipExit, StructuralStop
from helpers import INST, NOW, envelope, make_decision, make_exit_plan, make_manager, make_plan
from risk_engine import IST

from oms import Account, Veto
from oms.exits import evaluate, freeze_fill_levels, freeze_atr_level

IDX = "NSE_IDX:NIFTY"
PE_INST = "NSE_FNO:NIFTY:2026-09-29:24400:PE"


def _enter(pm, clock, plan, lots=2, *, inst=INST, fill_ctx=None):
    if fill_ctx:
        # client_order_id is derived from SIG in make_plan
        from helpers import SIG
        from contracts.ids import order_id

        pm.remember_fill_context(order_id("founder", SIG, "entry"), **fill_ctx)
    out = pm.router.submit(
        make_plan(), make_decision(lots=lots, instrument_id=inst), Account("founder"), exit_plan=plan
    )
    assert not isinstance(out, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    pm.router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=inst)
    )
    assert pm.open_book()
    return pm.open_book()[0]


def _bar(ts, close: float, inst: str = IDX, **extra):
    payload = {"instrument_id": inst, "c": close, "o": close, "h": close, "l": close}
    payload.update(extra)
    return envelope("BAR_CLOSED", ts, payload)


def test_structural_stop_bar_close_exact_time_and_price(tmp_path):
    plan = make_exit_plan(
        structural=StructuralStop(level=Level(kind="underlying", price=24400.0), trigger="bar_close")
    )
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, plan)
    clock.advance_to(NOW.replace(hour=10, minute=15))
    # tick beyond the level must not fire (bar_close trigger)
    pm.on_market(
        envelope(
            "TICK",
            clock.now(),
            {"instrument_id": INST, "ltp": 151.10, "underlying_ltp": 24390.0},
        )
    )
    assert pm.open_book()
    fire_ts = clock.now()
    fired = pm.on_market(_bar(fire_ts, 24390.0, underlying_close=24390.0))
    assert fired and fired[0].reason == "STRUCTURAL_STOP"
    assert fired[0].plan_field == "structural"
    assert clock.now() == fire_ts
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] == pytest.approx(151.10)


def test_atr_stop_fixed_at_fill_exact_time_and_price(tmp_path):
    plan = make_exit_plan(atr=AtrStop(k=1.5, trigger="bar_close"))
    entry_under, atr14 = 24500.0, 20.0
    expect = freeze_atr_level("CE", entry_under, 1.5, atr14)
    assert expect == pytest.approx(24470.0)
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan, fill_ctx={"entry_underlying": entry_under, "atr14": atr14})
    assert row["atr_stop_level"] == pytest.approx(24470.0)
    clock.advance_to(NOW.replace(hour=10, minute=18))
    # a later ATR print must not move the frozen level
    row["atr14"] = 80.0
    pm.on_market(_bar(clock.now(), 24480.0, underlying_close=24480.0))
    assert pm.open_book()
    fire_ts = clock.now()
    fired = pm.on_market(_bar(fire_ts, 24470.0, underlying_close=24470.0, event_id="e2"))
    assert fired and fired[0].reason == "ATR_STOP"
    assert fired[0].plan_field == "atr"
    assert clock.now() == fire_ts
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] == pytest.approx(151.10)


def test_signal_flip_own_opposite_on_bar_close(tmp_path):
    plan = make_exit_plan(
        signal_flip=SignalFlipExit(on=("own_opposite",), trigger="bar_close")
    )
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan)
    row["strategy_id"] = "TEST-A"
    clock.advance_to(NOW.replace(hour=10, minute=20))
    pm.on_market(
        envelope(
            "SIGNAL",
            clock.now(),
            {"strategy_id": "TEST-A", "side": "PE", "underlying": "NIFTY"},
        )
    )
    assert pm.open_book()  # waits for bar close
    fire_ts = clock.now()
    fired = pm.on_market(_bar(fire_ts, 24500.0, underlying_close=24500.0))
    assert fired and fired[0].reason == "SIGNAL_FLIP"
    assert fired[0].plan_field == "signal_flip"
    assert clock.now() == fire_ts
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] == pytest.approx(151.10)


def test_signal_flip_boss_opposite_on_bar_close(tmp_path):
    plan = make_exit_plan(
        signal_flip=SignalFlipExit(on=("boss_opposite",), trigger="bar_close")
    )
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, plan)
    clock.advance_to(NOW.replace(hour=10, minute=22))
    pm.on_market(
        envelope(
            "DECISION",
            clock.now(),
            {
                "decision": "ENTER",
                "underlying": "NIFTY",
                "side": "PE",
                "instrument_id": PE_INST,
            },
        )
    )
    assert pm.open_book()
    fire_ts = clock.now()
    fired = pm.on_market(_bar(fire_ts, 24510.0, underlying_close=24510.0))
    assert fired and fired[0].reason == "SIGNAL_FLIP"
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] == pytest.approx(151.10)


def test_evaluate_table_structural_atr_flip_exact():
    """Pure evaluate table: exact reason, field, and no fire on the wrong event."""
    fill = datetime(2026, 9, 28, 10, 1, tzinfo=IST)
    structural = make_exit_plan(
        structural=StructuralStop(level=Level(kind="underlying", price=24400.0))
    )
    pos = {
        "instrument_id": INST,
        "net_qty": 130,
        "orig_qty": 130,
        "avg_price": 151.10,
        "stop_price": 140.0,
        "exit_plan": structural,
        "fill_ts": fill,
        "last_good_quote": 151.10,
    }
    tick = evaluate(
        pos,
        fill + timedelta(minutes=2),
        mark=151.10,
        quote_ts=fill,
        event_kind="TICK",
        underlying=24350.0,
    )
    assert tick is None
    hit = evaluate(
        pos,
        fill + timedelta(minutes=2),
        mark=151.10,
        quote_ts=fill,
        event_kind="BAR_CLOSED",
        underlying=24350.0,
    )
    assert hit is not None
    assert hit.reason == "STRUCTURAL_STOP"
    assert hit.plan_field == "structural"

    atr_plan = make_exit_plan(atr=AtrStop(k=2.0, trigger="bar_close"))
    atr_pos = dict(pos)
    atr_pos["exit_plan"] = atr_plan
    freeze_fill_levels(
        atr_pos, atr_plan, 151.10, 130, entry_underlying=24500.0, atr14=10.0
    )
    assert atr_pos["atr_stop_level"] == pytest.approx(24480.0)
    miss = evaluate(
        atr_pos,
        fill + timedelta(minutes=3),
        mark=151.10,
        quote_ts=fill,
        event_kind="BAR_CLOSED",
        underlying=24490.0,
    )
    assert miss is None
    atr_hit = evaluate(
        atr_pos,
        fill + timedelta(minutes=3),
        mark=151.10,
        quote_ts=fill,
        event_kind="BAR_CLOSED",
        underlying=24480.0,
    )
    assert atr_hit is not None and atr_hit.reason == "ATR_STOP"

    flip_plan = make_exit_plan(signal_flip=SignalFlipExit(on=("own_opposite", "boss_opposite")))
    flip_pos = dict(pos)
    flip_pos["exit_plan"] = flip_plan
    assert (
        evaluate(
            flip_pos,
            fill + timedelta(minutes=4),
            mark=151.10,
            quote_ts=fill,
            event_kind="BAR_CLOSED",
            own_opposite=True,
        ).reason
        == "SIGNAL_FLIP"
    )
    flip_pos.pop("flip_pending", None)
    assert (
        evaluate(
            flip_pos,
            fill + timedelta(minutes=4),
            mark=151.10,
            quote_ts=fill,
            event_kind="BAR_CLOSED",
            boss_opposite=True,
        ).reason
        == "SIGNAL_FLIP"
    )


def test_grace_is_not_required_on_v2_09_plans(tmp_path):
    """V2-09 plans without grace still fire time/target; safeguards stay on."""
    from contracts.payloads import TimeStop

    plan = make_exit_plan(time_stops=(TimeStop(after_s=5, when="always"),))
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan)
    clock.advance_to(row["fill_ts"] + timedelta(seconds=5))
    fired = pm.on_market(envelope("CLOCK", clock.now(), {"minute": "10:01"}))
    assert fired and fired[0].reason == "TIME_EXIT"
    clock.advance_by(timedelta(milliseconds=200))
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 150.00, "ask": 150.20, "ltp": 150.10},
        )
    )
    assert not pm.open_book()
    pm.assert_stop_invariant()
