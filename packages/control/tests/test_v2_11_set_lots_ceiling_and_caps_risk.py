"""SET_LOTS rejects above the config ceiling and below 1; accepted cap binds risk."""

from __future__ import annotations

from contracts.clock import SimClock
from contracts.ids import order_id
from helpers import NOW, make_decision, make_handler, make_plan, make_router
from oms import Account, PositionManager, Veto
from risk_engine import TradeIntent

from control.handler import submit
from control.kinds import LOTS_CAP, lots_ceiling


def test_v2_11_set_lots_ceiling_and_caps_risk(tmp_path) -> None:
    assert lots_ceiling() == 25
    clock = SimClock(NOW)
    router = make_router(tmp_path, clock)
    handler = make_handler(tmp_path, clock, manager=PositionManager(clock=clock, router=router))

    high = submit(handler, "SET_LOTS", {"lots": 26}, actor="sahil", reason="too big", command_id="lots-hi")
    assert high["status"] == "rejected"
    assert "lots" in str(high.get("status_reason") or high.get("reject_reason"))

    low = submit(handler, "SET_LOTS", {"lots": 0}, actor="sahil", reason="too small", command_id="lots-lo")
    assert low["status"] == "rejected"

    ok = submit(handler, "SET_LOTS", {"lots": 1}, actor="sahil", reason="one lot", command_id="lots-one")
    assert ok["status"] == "applied"
    assert handler.risk.lots_cap == 1

    two = router.submit(
        make_plan(signal_id="lots-2", client_order_id=order_id("founder", "lots-2", "entry")),
        make_decision(lots=2, signal_ids=["lots-2"]),
        Account("founder"),
    )
    assert isinstance(two, Veto) and two.reason_code == LOTS_CAP

    intent = TradeIntent(
        symbol="NIFTY 24400 CE",
        side="BUY",
        lots=2,
        lot_size=65,
        order_type="LIMIT",
        price=151.40,
        decision_price=151.40,
        stop_loss=140.0,
        purpose="ENTRY",
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        client_order_id="risk-lots-2",
    )
    rd = handler.risk.check_entry(intent, now=clock.now())
    assert rd.approved is False
    assert rd.reason_code == LOTS_CAP
