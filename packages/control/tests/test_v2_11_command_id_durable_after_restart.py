"""Resent command_id after restart/rebuild is a no-op and returns the original ack."""

from __future__ import annotations

from contracts.clock import SimClock
from contracts.ids import order_id
from helpers import NOW, make_decision, make_handler, make_plan, make_router
from oms import Account, PositionManager, Veto

from control.handler import ControlHandler, submit
from control.kinds import PAUSED
from control.store import MemoryCommandStore


def test_v2_11_command_id_durable_after_restart(tmp_path) -> None:
    clock = SimClock(NOW)
    first = make_handler(tmp_path, clock)
    original = submit(first, "PAUSE", {"minutes": 20}, actor="sahil", reason="halt", command_id="dur-pause")
    assert original["status"] == "applied"

    rebuilt_store = MemoryCommandStore()
    second = ControlHandler(store=rebuilt_store, root=tmp_path, clock=clock)
    resent = submit(second, "PAUSE", {"minutes": 20}, actor="sahil", reason="halt", command_id="dur-pause")
    assert resent["status"] == "applied"
    assert resent["command_id"] == "dur-pause"
    assert resent.get("applied_ts") == original.get("applied_ts")
    assert rebuilt_store.get("dur-pause") is not None

    router = make_router(tmp_path, clock)
    second.manager = PositionManager(clock=clock, router=router)
    router.controls = second
    blocked = router.submit(
        make_plan(signal_id="dur-sig", client_order_id=order_id("founder", "dur-sig", "entry")),
        make_decision(signal_ids=["dur-sig"]),
        Account("founder"),
    )
    assert isinstance(blocked, Veto) and blocked.reason_code == PAUSED
