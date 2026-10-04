"""Whole-lot exits: partials, 1-lot skip, and every exit qty % lot_size == 0."""

from __future__ import annotations

from datetime import timedelta

from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from contracts.payloads import Level, Partial, TimeStop
from helpers import INST, NOW, envelope, make_decision, make_exit_plan, make_manager, make_plan
from hypothesis import given, settings
from hypothesis import strategies as st

from oms import Account, Veto, lot_size_for
from oms.exits import (
    evaluate,
    instrument_lot_size,
    partial_exit_qty,
    plan_as_json,
    plan_from_mapping,
    whole_lots_qty,
)

NIFTY_LOT = lot_size_for(INST)
BN_INST = "NSE_FNO:BANKNIFTY:2026-09-29:55000:CE"
SX_INST = "NSE_FNO:SENSEX:2026-09-29:81000:CE"


def _enter(pm, clock, plan, lots: int, inst: str = INST):
    out = pm.router.submit(
        make_plan(),
        make_decision(lots=lots, instrument_id=inst, underlying=inst.split(":")[1]),
        Account("founder"),
        exit_plan=plan,
    )
    assert not isinstance(out, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    pm.router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=inst)
    )
    return pm.open_book()[0]


def test_three_lots_half_partial_leaves_two_lots(tmp_path) -> None:
    plan = make_exit_plan(partials=(Partial(at=Level(kind="premium", price=155.0), fraction=0.5),))
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan, lots=3)
    assert row["net_qty"] == 3 * NIFTY_LOT
    clock.advance_to(NOW.replace(minute=20))
    fired = pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 155.00, "ask": 155.20, "ltp": 155.10},
        )
    )
    assert fired and fired[0].reason == "PARTIAL"
    assert fired[0].qty == NIFTY_LOT
    assert fired[0].qty % NIFTY_LOT == 0
    book = pm.open_book()
    assert len(book) == 1
    assert book[0]["net_qty"] == 2 * NIFTY_LOT


def test_one_lot_half_partial_is_skipped(tmp_path) -> None:
    plan = make_exit_plan(partials=(Partial(at=Level(kind="premium", price=155.0), fraction=0.5),))
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, plan, lots=1)
    clock.advance_to(NOW.replace(minute=20))
    fired = pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 155.00, "ask": 155.20, "ltp": 155.10},
        )
    )
    assert fired == []
    book = pm.open_book()
    assert len(book) == 1
    assert book[0]["net_qty"] == NIFTY_LOT


def test_odd_lot_count_three_lots_third_partial_sells_one_lot(tmp_path) -> None:
    plan = make_exit_plan(partials=(Partial(at=Level(kind="premium", price=155.0), fraction=0.33),))
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, plan, lots=3)
    clock.advance_to(NOW.replace(minute=20))
    fired = pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 155.00, "ask": 155.20, "ltp": 155.10},
        )
    )
    assert fired and fired[0].reason == "PARTIAL"
    assert fired[0].qty == NIFTY_LOT  # floor(0.99)=0 → min 1 lot
    assert pm.open_book()[0]["net_qty"] == 2 * NIFTY_LOT


def test_partial_exit_qty_helper_table() -> None:
    assert (
        partial_exit_qty(orig_qty=195, net_qty=195, fraction=0.5, instrument_id=INST) == NIFTY_LOT
    )
    assert partial_exit_qty(orig_qty=65, net_qty=65, fraction=0.5, instrument_id=INST) is None
    assert (
        partial_exit_qty(orig_qty=195, net_qty=195, fraction=0.33, instrument_id=INST) == NIFTY_LOT
    )
    bn = instrument_lot_size(BN_INST)
    assert bn == 30
    assert partial_exit_qty(orig_qty=90, net_qty=90, fraction=0.5, instrument_id=BN_INST) == 30


def test_ledger_rejects_non_lot_fill(tmp_path) -> None:
    from oms import MemoryLedger

    store = MemoryLedger()
    try:
        store.record_fill("oid", 98, 151.4, fill_model="depth", instrument_id=INST)
    except ValueError as exc:
        assert "lot size" in str(exc)
    else:
        raise AssertionError("odd fill qty must be refused")


def _eval_pos(
    inst: str,
    lots: int,
    *,
    fraction: float = 0.5,
    mark: float | None = 155.1,
    founder_kind: str | None = None,
    kill: bool = False,
    strategy_exit: bool = False,
    now=None,
    time_stop: bool = False,
):
    lot = instrument_lot_size(inst)
    qty = lots * lot
    plan = make_exit_plan(
        partials=(Partial(at=Level(kind="premium", price=155.0), fraction=fraction),),
        target=Level(kind="premium", price=200.0),
        time_stops=(TimeStop(after_s=1, when="always"),),
        flat_by_ist="15:15",
    )
    pos = {
        "instrument_id": inst,
        "net_qty": qty,
        "orig_qty": qty,
        "avg_price": 151.40,
        "stop_price": 140.0,
        "exit_plan": plan,
        "fill_ts": NOW,
        "partials_done": 0,
        "last_good_quote": 151.4,
        "chosen_time_stop": plan.time_stops[0] if time_stop else None,
    }
    return evaluate(
        pos,
        now or NOW.replace(minute=20),
        mark=mark,
        quote_ts=NOW,
        kill=kill,
        founder_kind=founder_kind,
        strategy_exit=strategy_exit,
    ), lot


@settings(max_examples=80, derandomize=True, deadline=500)
@given(
    symbol=st.sampled_from(
        [
            INST,
            BN_INST,
            SX_INST,
        ]
    ),
    lots=st.integers(min_value=1, max_value=8),
    fraction=st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False),
    path=st.sampled_from(
        ["founder", "kill", "eod", "partial", "target", "time", "strategy", "catastrophic"]
    ),
)
def test_every_exit_qty_is_a_lot_multiple(
    symbol: str, lots: int, fraction: float, path: str
) -> None:
    kwargs: dict = {"fraction": fraction}
    if path == "founder":
        kwargs["founder_kind"] = "CUT_LOSS"
    elif path == "kill":
        kwargs["kill"] = True
    elif path == "eod":
        kwargs["now"] = NOW.replace(hour=15, minute=15)
        kwargs["mark"] = 151.4
    elif path == "target":
        kwargs["mark"] = 200.1
        kwargs["fraction"] = 0.01  # 1-lot skip still allows target
    elif path == "time":
        kwargs["time_stop"] = True
        kwargs["now"] = NOW + timedelta(seconds=2)
        kwargs["mark"] = 151.4
    elif path == "strategy":
        kwargs["strategy_exit"] = True
        kwargs["mark"] = 151.4
    elif path == "catastrophic":
        kwargs["mark"] = 139.0
    req, lot = _eval_pos(symbol, lots, **kwargs)
    if req is None:
        assert path == "partial" and lots == 1
        return
    assert req.qty % lot == 0
    if req.reason == "PARTIAL":
        assert req.qty >= lot
        leftover = lots * lot - req.qty
        assert leftover % lot == 0
        assert leftover >= lot


def test_whole_lots_qty_snaps_down() -> None:
    assert whole_lots_qty(195, NIFTY_LOT) == 195
    assert whole_lots_qty(194, NIFTY_LOT) == 130
    assert whole_lots_qty(64, NIFTY_LOT) == 0


def test_plan_roundtrip_keeps_partial_fraction() -> None:
    plan = make_exit_plan(partials=(Partial(at=Level(kind="premium", price=155.0), fraction=0.5),))
    again = plan_from_mapping(plan_as_json(plan))
    assert again.partials[0].fraction == 0.5
