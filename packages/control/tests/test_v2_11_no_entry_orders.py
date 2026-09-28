"""flatten/kill cannot place a new entry order"""

from __future__ import annotations

from helpers import make_handler, open_one

from control.handler import submit


def test_v2_11_flatten_kill_cannot_place_entry(tmp_path) -> None:
    pm, clock = open_one(tmp_path)
    before = {oid for oid, order in pm.router.broker.orders.items() if order.intent.purpose == "ENTRY"}
    handler = make_handler(tmp_path, clock, manager=pm)
    kill = submit(handler, "KILL", {}, actor="sahil", reason="no-entry", command_id="ne-1")
    assert kill["status"] == "applied"
    after = {oid for oid, order in pm.router.broker.orders.items() if order.intent.purpose == "ENTRY"}
    assert after == before
    assert handler.entry_orders == []
    for order in pm.router.broker.orders.values():
        if order.intent.purpose == "ENTRY":
            continue
        assert order.intent.purpose in {"EXIT", "STOP"} or order.intent.side == "SELL"
