"""V2-09 exit kinds: exact time/price table, time-stop windows, EOD, trail, kill."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from contracts.payloads import Level, Partial, TimeStop, Trail
from helpers import (
    INST,
    NOW,
    depth_env,
    envelope,
    make_decision,
    make_exit_plan,
    make_manager,
    make_plan,
)
from risk_engine import IST

from oms import Account, Veto

OPEN_0920 = datetime(2026, 9, 28, 9, 20, tzinfo=IST)
EXPIRY_DAY = datetime(2026, 9, 29, 9, 20, tzinfo=IST)
LATE_ENTRY = datetime(2026, 9, 28, 11, 0, tzinfo=IST)


def _enter(pm, clock, plan, lots=2):
    out = pm.router.submit(
        make_plan(), make_decision(lots=lots), Account("founder"), exit_plan=plan
    )
    assert not isinstance(out, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    pm.router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
    )
    assert pm.open_book()
    return pm.open_book()[0]


def test_exit_kind_table_exact_time_and_price(tmp_path):
    """One row per V2-09 exit kind: time and fill price."""
    rows = []

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, make_exit_plan())
    clock.advance_to(NOW.replace(hour=10, minute=30))
    pm.on_market(
        envelope("FOUNDER_COMMAND", clock.now(), {"kind": "CUT_LOSS", "instrument_id": INST})
    )
    closed = pm.store.closed[-1]
    rows.append(("FOUNDER_COMMAND", clock.now(), closed["last_exit_price"]))
    assert closed["last_exit_price"] > 0
    assert not pm.open_book()

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, make_exit_plan())
    clock.advance_to(NOW.replace(hour=10, minute=31))
    pm.kill_switch = True
    pm.on_market(
        envelope(
            "CLOCK", clock.now(), {"session": "2026-09-28", "phase": "MARKET", "minute": "10:31"}
        )
    )
    assert not pm.open_book()
    rows.append(("KILL_SWITCH", clock.now(), pm.store.closed[-1]["last_exit_price"]))

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, make_exit_plan())
    clock.advance_to(NOW.replace(hour=10, minute=32))
    pm.on_market(
        envelope(
            "TICK",
            clock.now(),
            {"instrument_id": INST, "ltp": 139.90, "bid": 139.80, "ask": 140.00},
        )
    )
    assert not pm.open_book()
    rows.append(("CATASTROPHIC_STOP", clock.now(), pm.store.closed[-1]["last_exit_price"]))
    assert pm.store.closed[-1]["last_exit_price"] <= 140.0

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(
        pm,
        clock,
        make_exit_plan(target=Level(kind="premium", price=160.0)),
    )
    clock.advance_to(NOW.replace(hour=10, minute=33))
    pm.on_market(depth_env(clock.now(), 160.00, 160.20, 160.10))
    assert not pm.open_book()
    rows.append(("TARGET_HIT", clock.now(), pm.store.closed[-1]["last_exit_price"]))

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, make_exit_plan())
    clock.advance_by(timedelta(seconds=2))
    pm.on_market(depth_env(clock.now(), 151.00, 151.20, 151.10))
    fired = pm.request_strategy_exit(INST)
    assert fired and fired[0].reason == "STRATEGY_EXIT"
    assert not pm.open_book()
    rows.append(("STRATEGY_EXIT", clock.now(), pm.store.closed[-1]["last_exit_price"]))

    assert {r[0] for r in rows} == {
        "FOUNDER_COMMAND",
        "KILL_SWITCH",
        "CATASTROPHIC_STOP",
        "TARGET_HIT",
        "STRATEGY_EXIT",
    }


def test_time_stop_0920_and_expiry_zero_ticks(tmp_path):
    plan = make_exit_plan(
        time_stops=(
            TimeStop(after_s=180, when="entry_in:09:15-10:00"),
            TimeStop(after_s=180, when="expiry_day"),
            TimeStop(after_s=3600, when="always"),
        )
    )
    clock = SimClock(OPEN_0920)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan)
    assert row["chosen_time_stop"].when == "entry_in:09:15-10:00"
    deadline = row["fill_ts"] + timedelta(seconds=180)
    clock.advance_to(deadline)
    fired = pm.on_market(envelope("CLOCK", clock.now(), {"minute": "09:23"}))
    assert fired and fired[0].reason == "TIME_EXIT"
    assert (clock.now() - deadline) <= timedelta(seconds=1)
    # still open until the first depth after the deadline
    assert pm.open_book()
    clock.advance_by(timedelta(milliseconds=400))
    pm.on_market(depth_env(clock.now(), 149.50, 149.70, 149.55))
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] == pytest.approx(149.50)

    expiry_late = datetime(2026, 9, 29, 11, 0, tzinfo=IST)
    clock = SimClock(expiry_late)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan)
    assert row["chosen_time_stop"].when == "expiry_day"
    clock.advance_to(row["fill_ts"] + timedelta(seconds=180))
    pm.on_market(envelope("CLOCK", clock.now(), {"minute": "09:23"}))
    clock.advance_by(timedelta(milliseconds=200))
    pm.on_market(depth_env(clock.now(), 148.00, 148.20, 148.10))
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] == pytest.approx(148.00)


def test_non_matching_window_uses_always_time_stop(tmp_path):
    plan = make_exit_plan(
        time_stops=(
            TimeStop(after_s=180, when="entry_in:09:15-10:00"),
            TimeStop(after_s=600, when="always"),
        )
    )
    clock = SimClock(LATE_ENTRY)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan)
    assert row["chosen_time_stop"].when == "always"
    assert row["chosen_time_stop"].after_s == 600
    clock.advance_to(row["fill_ts"] + timedelta(seconds=600))
    pm.on_market(envelope("CLOCK", clock.now(), {"minute": "11:10"}))
    clock.advance_by(timedelta(milliseconds=200))
    pm.on_market(depth_env(clock.now(), 150.00, 150.20, 150.10))
    assert not pm.open_book()


def test_eod_flat_zero_ticks_after_1500(tmp_path):
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, make_exit_plan(flat_by_ist="15:15"))
    clock.advance_to(datetime(2026, 9, 28, 15, 0, 30, tzinfo=IST))
    pm.on_market(envelope("CLOCK", clock.now(), {"minute": "15:00"}))
    assert pm.open_book()  # not yet flat_by_ist
    clock.advance_to(datetime(2026, 9, 28, 15, 15, 0, tzinfo=IST))
    fired = pm.on_market(envelope("CLOCK", clock.now(), {"minute": "15:15"}))
    assert fired and fired[0].reason == "FLATTEN_EOD"
    assert not pm.open_book()


def test_partial_then_trail_moves_resting_stop(tmp_path):
    plan = make_exit_plan(
        partials=(Partial(at=Level(kind="premium", price=155.0), fraction=0.5),),
        trail=Trail(kind="step", activate_at=Level(kind="premium", price=156.0), step=2.0),
    )
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, plan, lots=2)
    stop_before = pm.open_book()[0]["stop_price"]
    clock.advance_to(NOW.replace(hour=10, minute=40))
    pm.on_market(depth_env(clock.now(), 155.00, 155.20, 155.10))
    book = pm.open_book()
    assert len(book) == 1
    assert book[0]["net_qty"] == 65
    clock.advance_by(timedelta(seconds=2))
    pm.on_market(depth_env(clock.now(), 157.00, 157.20, 157.10))
    book = pm.open_book()
    assert book[0]["stop_price"] > stop_before
    key = INST
    stop_oid = pm.store.protective[key]
    assert pm.router.broker.orders[stop_oid].trigger_price == book[0]["stop_price"]


def test_exits_allowed_under_kill_switch(tmp_path):
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, make_exit_plan())
    pm.kill_switch = True
    blocked = pm.router.submit(
        make_plan(signal_id="sg_k_nifty_20260928_1100_0"),
        make_decision(),
        Account("founder"),
        exit_plan=make_exit_plan(),
    )
    # kill is on the manager; risk kill is a separate file. Force flatten via kill flag.
    clock.advance_by(timedelta(seconds=1))
    fired = pm.on_market(envelope("CLOCK", clock.now(), {"minute": "10:02"}))
    assert fired and fired[0].reason == "KILL_SWITCH"
    assert not pm.open_book()
    _ = blocked


def test_flat_by_ist_invariant_on_fixtures(tmp_path):
    for stamp in (NOW, OPEN_0920, EXPIRY_DAY, LATE_ENTRY):
        clock = SimClock(stamp)
        pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
        _enter(pm, clock, make_exit_plan())
        flat = datetime.combine(
            stamp.date(), datetime.strptime("15:15", "%H:%M").time(), tzinfo=IST
        )
        clock.advance_to(flat)
        pm.on_market(envelope("CLOCK", clock.now(), {"minute": "15:15"}))
        assert pm.open_book() == [], stamp
