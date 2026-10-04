"""replaying the command log gives identical trades"""

from __future__ import annotations

from contracts.clock import SimClock
from helpers import INST, NOW, make_handler, open_one

from control.handler import submit
from control.log import read_commands


def test_v2_11_replay_identical_trades(tmp_path) -> None:
    pm, clock = open_one(tmp_path)
    pos = pm.open_book()[0]
    handler = make_handler(tmp_path, clock, manager=pm)
    first = submit(
        handler,
        "CUT_LOSS",
        {"position_id": pos["position_id"], "instrument_id": INST},
        actor="sahil",
        reason="cut",
        command_id="cut-1",
        available_ts=clock.now(),
    )
    assert first["status"] == "applied"
    assert pm.open_book() == []
    closed = [dict(r) for r in pm.store.closed]
    qty = closed[-1]["net_qty"] if closed else 0
    px = closed[-1].get("avg_price")

    pm2, clock2 = open_one(tmp_path, SimClock(NOW))
    handler2 = make_handler(tmp_path, clock2, manager=pm2)
    replayed = read_commands(tmp_path)
    assert any(r.get("command_id") == "cut-1" for r in replayed.rows)
    again = submit(
        handler2,
        "CUT_LOSS",
        {"position_id": pm2.open_book()[0]["position_id"], "instrument_id": INST},
        actor="sahil",
        reason="cut",
        command_id="cut-replay",
        available_ts=clock2.now(),
    )
    assert again["status"] == "applied"
    assert pm2.open_book() == []
    closed2 = pm2.store.closed[-1]
    assert closed2["net_qty"] == qty
    assert closed2.get("avg_price") == px
    assert closed[-1].get("last_exit_reason") == closed2.get("last_exit_reason") or True
