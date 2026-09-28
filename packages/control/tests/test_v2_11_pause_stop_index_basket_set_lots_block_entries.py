"""PAUSE / STOP / INDEX / BASKET_REMOVE / SET_LOTS block OrderRouter.submit."""

from __future__ import annotations

from datetime import timedelta

from contracts.clock import SimClock
from contracts.ids import order_id
from helpers import INST, NOW, SIG, make_decision, make_handler, make_plan, make_router
from oms import Account, PositionManager, Veto

from control.handler import submit
from control.kinds import BASKET_REMOVED, INDEX_DISABLED, LOTS_CAP, PAUSED, STOPPED


def _count_places(router: object) -> list[int]:
    calls: list[int] = []
    inner = router.broker.place_order

    def counted(intent: object, rd: object) -> object:
        calls.append(1)
        return inner(intent, rd)

    router.broker.place_order = counted  # type: ignore[method-assign]
    return calls


def _submit(router: object, sig: str, lots: int = 1) -> object:
    plan = make_plan(signal_id=sig, client_order_id=order_id("founder", sig, "entry"))
    return router.submit(plan, make_decision(lots=lots, signal_ids=[sig]), Account("founder"))


def test_v2_11_pause_stop_index_basket_set_lots_block_entries(tmp_path) -> None:
    clock = SimClock(NOW)
    router = make_router(tmp_path, clock)
    handler = make_handler(tmp_path, clock, manager=PositionManager(clock=clock, router=router))
    places = _count_places(router)

    submit(handler, "PAUSE", {"minutes": 10}, actor="sahil", reason="lunch", command_id="blk-pause")
    out = _submit(router, "sig-pause")
    assert isinstance(out, Veto) and out.reason_code == PAUSED
    assert places == []

    submit(handler, "PAUSE", {"minutes": 0}, actor="sahil", reason="resume", command_id="blk-resume")
    submit(handler, "START", {}, actor="sahil", reason="go", command_id="blk-start")
    ok = _submit(router, "sig-after-resume")
    assert not isinstance(ok, Veto)
    assert len(places) == 1

    submit(handler, "STOP", {}, actor="sahil", reason="halt", command_id="blk-stop")
    stopped = _submit(router, "sig-stop")
    assert isinstance(stopped, Veto) and stopped.reason_code == STOPPED
    assert len(places) == 1
    submit(handler, "START", {}, actor="sahil", reason="again", command_id="blk-start2")

    submit(
        handler,
        "INDEX",
        {"underlying": "NIFTY", "enabled": False},
        actor="sahil",
        reason="skip nifty",
        command_id="blk-idx",
    )
    idx = _submit(router, "sig-idx")
    assert isinstance(idx, Veto) and idx.reason_code == INDEX_DISABLED
    assert len(places) == 1
    submit(
        handler,
        "INDEX",
        {"underlying": "NIFTY", "enabled": True},
        actor="sahil",
        reason="nifty on",
        command_id="blk-idx-on",
    )

    submit(
        handler,
        "BASKET_REMOVE",
        {"strategy_id": SIG},
        actor="sahil",
        reason="drop",
        command_id="blk-bsk",
    )
    basket = _submit(router, SIG)
    assert isinstance(basket, Veto) and basket.reason_code == BASKET_REMOVED
    assert len(places) == 1

    submit(handler, "SET_LOTS", {"lots": 1}, actor="sahil", reason="cap", command_id="blk-lots")
    capped = _submit(router, "sig-lots2", lots=2)
    assert isinstance(capped, Veto) and capped.reason_code == LOTS_CAP
    assert len(places) == 1
    clock.advance_by(timedelta(seconds=61))
    one = _submit(router, "sig-lots1", lots=1)
    assert not isinstance(one, Veto)
    assert len(places) == 2
    assert INST
