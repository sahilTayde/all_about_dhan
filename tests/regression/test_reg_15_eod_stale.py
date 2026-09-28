"""REG-15a-d: EOD flatten is never held by the stale-quote guard (K16)."""

from __future__ import annotations

from datetime import datetime, timedelta

from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from helpers import (
    INST,
    NOW,
    envelope,
    make_decision,
    make_exit_plan,
    make_manager,
    make_plan,
)
from oms import Account, Veto
from risk_engine import IST

LAST_GOOD = 150.25


def _open_and_stale_from(tmp_path, start, stale_from):
    clock = SimClock(start)
    broker = make_broker(clock=clock)
    pm = make_manager(tmp_path, clock, broker=broker)
    order = pm.router.submit(
        make_plan(),
        make_decision(lots=2),
        Account("founder"),
        exit_plan=make_exit_plan(),
    )
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
    clock.advance_to(stale_from)
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {
                "instrument_id": INST,
                "bid": LAST_GOOD,
                "ask": LAST_GOOD + 0.20,
                "ltp": LAST_GOOD,
            },
        )
    )
    return clock, pm


def test_reg_15a_eod_sent_at_1515_even_when_quotes_stale(tmp_path) -> None:
    clock, pm = _open_and_stale_from(
        tmp_path, NOW, datetime(2026, 9, 28, 15, 10, tzinfo=IST)
    )
    clock.advance_to(datetime(2026, 9, 28, 15, 15, 0, tzinfo=IST))
    fired = pm.on_market(envelope("CLOCK", clock.now(), {"minute": "15:15"}))
    assert fired and fired[0].reason == "FLATTEN_EOD"
    assert clock.now().strftime("%H:%M") == "15:15"


def test_reg_15b_eod_priced_at_last_good_flagged_stale_quote(tmp_path) -> None:
    clock, pm = _open_and_stale_from(
        tmp_path, NOW, datetime(2026, 9, 28, 15, 10, tzinfo=IST)
    )
    clock.advance_to(datetime(2026, 9, 28, 15, 15, 0, tzinfo=IST))
    fired = pm.on_market(envelope("CLOCK", clock.now(), {"minute": "15:15"}))
    assert fired and fired[0].stale_quote is True
    assert any(a["reason_code"] == "STALE_QUOTE" for a in pm.alerts)
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] == LAST_GOOD


def test_reg_15c_ordinary_exits_wait_for_fresh_quote(tmp_path) -> None:
    clock = SimClock(NOW)
    broker = make_broker(clock=clock)
    pm = make_manager(tmp_path, clock, broker=broker)
    plan = make_exit_plan()
    # target ordinary exit should wait while the quote is stale
    from contracts.payloads import Level

    plan = make_exit_plan(target=Level(kind="premium", price=160.0))
    order = pm.router.submit(
        make_plan(), make_decision(), Account("founder"), exit_plan=plan
    )
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
    clock.advance_by(timedelta(seconds=120))  # last good is now > 90s old
    # mark is still 151.10 (below target) and stale — even a strategy exit waits
    fired = pm.request_strategy_exit(INST)
    assert fired == []
    assert pm.open_book()
    clock.advance_by(timedelta(seconds=1))
    fired = pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 151.00, "ask": 151.20, "ltp": 151.10},
        )
    )
    assert fired and fired[0].reason == "STRATEGY_EXIT"
    assert not pm.open_book()


def test_reg_15d_no_position_open_after_flat_by_ist(tmp_path) -> None:
    clock, pm = _open_and_stale_from(
        tmp_path, NOW, datetime(2026, 9, 28, 15, 10, tzinfo=IST)
    )
    clock.advance_to(datetime(2026, 9, 28, 15, 15, 0, tzinfo=IST))
    pm.on_market(envelope("CLOCK", clock.now(), {"minute": "15:15"}))
    assert pm.open_book() == []
