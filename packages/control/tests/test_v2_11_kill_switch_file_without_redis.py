"""with Redis stopped, the kill-switch file still vetoes entries and the CLI flatten closes paper positions"""

from __future__ import annotations

from helpers import INST, make_handler, open_one
from risk_engine import TradeIntent

from control.flatten import flatten_paper
from control.handler import submit


def test_v2_11_kill_switch_file_without_redis(tmp_path) -> None:
    pm, clock = open_one(tmp_path)
    handler = make_handler(tmp_path, clock, manager=pm)
    submit(handler, "KILL", {}, actor="sahil", reason="file", command_id="k-file")
    assert handler.kill_switch_path.is_file()
    # No Redis: talk to risk + paper book directly.
    intent = TradeIntent(
        client_order_id="no-redis",
        symbol="NIFTY 24400 CE",
        instrument_id=INST,
        side="BUY",
        lots=1,
        lot_size=65,
        purpose="ENTRY",
        order_type="MARKET",
    )
    veto = pm.router.risk.check_entry(intent, now=clock.now())
    assert veto.approved is False and veto.reason_code == "KILL_SWITCH"

    flat_root = tmp_path / "flat"
    flat_root.mkdir()
    pm2, clock2 = open_one(flat_root)
    out = flatten_paper(account="founder", clock=clock2, risk=pm2.router.risk, manager=pm2, reason="cli")
    assert out["ok"] is True
    assert pm2.open_book() == []
    assert "FOUNDER_COMMAND" in out["exits"] or out["exits"]
