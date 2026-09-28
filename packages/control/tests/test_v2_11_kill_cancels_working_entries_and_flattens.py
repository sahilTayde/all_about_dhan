"""KILL cancels unfilled ENTRY orders and flattens open positions (whole lots)."""

from __future__ import annotations

from datetime import timedelta

from helpers import make_decision, make_exit_plan, make_handler, make_plan, open_one
from oms import Account, Veto

from control.handler import submit


def test_v2_11_kill_cancels_working_entries_and_flattens(tmp_path) -> None:
    pm, clock = open_one(tmp_path)
    handler = make_handler(tmp_path, clock, manager=pm)
    clock.advance_by(timedelta(seconds=61))
    alt = "NSE_FNO:NIFTY:2026-09-29:24500:CE"
    working = pm.router.submit(
        make_plan(signal_id="sig-working", client_order_id="ord-working"),
        make_decision(signal_ids=["sig-working"], instrument_id=alt),
        Account("founder"),
        exit_plan=make_exit_plan(),
    )
    assert not isinstance(working, Veto)
    assert working.is_open
    assert working.intent.purpose == "ENTRY"
    assert pm.open_book()

    ack = submit(handler, "KILL", {}, actor="sahil", reason="panic", command_id="kill-work")
    assert ack["status"] == "applied"
    assert "ord-working" in (ack.get("cancelled_entries") or []) or not working.is_open
    assert not working.is_open
    assert pm.open_book() == []
    sells = [
        o
        for o in pm.router.broker.orders.values()
        if getattr(o.intent, "purpose", "") == "EXIT" and getattr(o.intent, "side", "") == "SELL"
    ]
    assert sells
    live_net = 65
    assert all(int(o.intent.qty) <= live_net for o in sells)
