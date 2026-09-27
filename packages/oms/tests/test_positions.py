"""V2-09 book: open, add, partial, full close. IST stamps. No look-ahead."""

from __future__ import annotations

from datetime import timedelta

import pytest
from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from helpers import INST, NOW, SIG, envelope, make_decision, make_exit_plan, make_manager, make_plan
from oms import Account, Veto
from risk_engine import IST


def _fill_entry(router, clock, inst=INST, bid=151.00, ask=151.20, ltp=151.10):
    clock.advance_by(timedelta(milliseconds=250))
    router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=bid, ask=ask, ltp=ltp, instrument_id=inst)
    )


def test_open_add_partial_full_close_pnl_ist(tmp_path):
    clock = SimClock(NOW)
    broker = make_broker(clock=clock)
    pm = make_manager(tmp_path, clock, broker=broker)
    plan = make_exit_plan()
    first = pm.router.submit(make_plan(), make_decision(lots=2), Account("founder"), exit_plan=plan)
    assert not isinstance(first, Veto)
    _fill_entry(pm.router, clock)
    book = pm.open_book()
    assert len(book) == 1
    assert book[0]["net_qty"] == 130
    assert book[0]["avg_price"] == 151.40
    assert book[0]["fill_ts"].tzinfo == IST
    assert book[0]["exit_plan_json"]["catastrophic"]["level"]["price"] == 140.0

    clock.advance_by(timedelta(minutes=4))
    add = pm.router.submit(
        make_plan(signal_id="sg_add_nifty_20260928_1005_0", plan_id="ep_2", decision_id="dc_2"),
        make_decision(decision_id="dc_2", lots=1),
        Account("founder"),
        exit_plan=plan,
    )
    assert not isinstance(add, Veto)
    _fill_entry(pm.router, clock)
    book = pm.open_book()
    assert book[0]["net_qty"] == 195
    assert abs(book[0]["avg_price"] - 151.40) < 1e-9

    clock.advance_to(NOW.replace(hour=10, minute=20))
    fired = pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 160.00, "ask": 160.20, "ltp": 160.10},
        )
    )
    # no target/partial in this plan — explicit strategy exit of 65
    book[0]["net_qty"] = 65
    work = dict(book[0])
    work["net_qty"] = 65
    work["exit_price_hint"] = 160.00
    work["exit_reason"] = "PARTIAL"
    pm.router.exit(work, "PARTIAL")
    pm.router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=160.00, ask=160.20, ltp=160.10, instrument_id=INST)
    )
    book = pm.open_book()
    assert len(book) == 1
    assert book[0]["net_qty"] == 130
    assert book[0]["realized_pnl"] > 0

    clock.advance_to(NOW.replace(hour=10, minute=45))
    pm.on_market(
        envelope("FOUNDER_COMMAND", clock.now(), {"kind": "CUT_LOSS", "instrument_id": INST})
    )
    assert pm.open_book() == []
    assert pm.store.closed
    assert pm.store.closed[-1]["last_exit_ts"].tzinfo == IST
    _ = fired


def test_no_lookahead_future_quote_ignored(tmp_path):
    clock = SimClock(NOW)
    broker = make_broker(clock=clock)
    pm = make_manager(tmp_path, clock, broker=broker)
    order = pm.router.submit(
        make_plan(), make_decision(), Account("founder"), exit_plan=make_exit_plan()
    )
    assert not isinstance(order, Veto)
    _fill_entry(pm.router, clock)
    future = NOW + timedelta(minutes=10)
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            future,
            {"instrument_id": INST, "bid": 100.00, "ask": 100.20, "ltp": 100.00},
        )
    )
    row = pm.open_book()[0]
    assert row["mark"] != 100.00
    assert row["last_good_quote"] != 100.00


def test_plan_without_catastrophic_refuses():
    from oms.exits import plan_from_mapping

    with pytest.raises(ValueError, match="catastrophic"):
        plan_from_mapping({"flat_by_ist": "15:15"})
    with pytest.raises(ValueError, match="catastrophic"):
        plan_from_mapping({"catastrophic": {}})


def test_naive_timestamp_rejected():
    from datetime import datetime

    from oms.exits import as_ist

    with pytest.raises(ValueError, match="timezone-aware"):
        as_ist(datetime(2026, 9, 28, 10, 0))
    _ = SIG
