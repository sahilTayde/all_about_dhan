"""KILL flattens and blocks until REARM"""

from __future__ import annotations

from helpers import INST, make_handler, open_one

from control.handler import submit


def test_v2_11_kill_flattens_and_blocks_until_rearm(tmp_path) -> None:
    pm, clock = open_one(tmp_path)
    handler = make_handler(tmp_path, clock, manager=pm)
    kill = submit(handler, "KILL", {}, actor="sahil", reason="panic", command_id="kill-1")
    assert kill["status"] == "applied"
    assert pm.open_book() == []
    assert handler.kill_switch_path.is_file()
    assert handler.allows_entry(clock.now(), underlying="NIFTY") == "FOUNDER_KILL_SWITCH"
    from risk_engine import TradeIntent

    rd = pm.router.risk.check_entry(
        TradeIntent(
            client_order_id="blocked",
            symbol="NIFTY 24400 CE",
            instrument_id=INST,
            side="BUY",
            lots=1,
            lot_size=65,
            purpose="ENTRY",
            order_type="MARKET",
        ),
        now=clock.now(),
    )
    assert rd.approved is False
    assert rd.reason_code == "KILL_SWITCH"
    rearm = submit(handler, "REARM", {}, actor="sahil", reason="clear", command_id="rearm-1")
    assert rearm["status"] == "applied"
    assert not handler.kill_switch_path.exists()
    assert handler.allows_entry(clock.now(), underlying="NIFTY") is None
    rd2 = pm.router.risk.check_entry(
        TradeIntent(
            client_order_id="after",
            symbol="NIFTY 24400 CE",
            instrument_id=INST,
            side="BUY",
            lots=1,
            lot_size=65,
            purpose="ENTRY",
            order_type="MARKET",
        ),
        now=clock.now(),
    )
    assert rd2.reason_code != "KILL_SWITCH" or rd2.approved
