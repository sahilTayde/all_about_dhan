"""V2-09b primitive table: structural, ATR (fixed at fill), signal-flip."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from contracts.payloads import AtrStop, Level, SignalFlipExit, StructuralStop
from helpers import INST, NOW, envelope, make_decision, make_exit_plan, make_manager, make_plan
from risk_engine import IST

from oms import Account, Veto
from oms.exits import (
    ExitRequest,
    assert_exit_reason,
    evaluate,
    freeze_atr_level,
    freeze_fill_levels,
    house_stop_premium,
)

IDX = "NSE_IDX:NIFTY"
PE_INST = "NSE_FNO:NIFTY:2026-09-29:24400:PE"


def _enter(pm, clock, plan, lots=2, *, inst=INST, fill_ctx=None):
    if fill_ctx:
        # client_order_id is derived from SIG in make_plan
        from contracts.ids import order_id
        from helpers import SIG

        pm.remember_fill_context(order_id("founder", SIG, "entry"), **fill_ctx)
    out = pm.router.submit(
        make_plan(),
        make_decision(lots=lots, instrument_id=inst),
        Account("founder"),
        exit_plan=plan,
    )
    assert not isinstance(out, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    pm.router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=inst)
    )
    assert pm.open_book()
    return pm.open_book()[0]


def _bar(ts, close: float, inst: str = IDX, **extra):
    payload = {"instrument_id": inst, "c": close, "o": close, "h": close, "l": close}
    payload.update(extra)
    return envelope("BAR_CLOSED", ts, payload)


def test_structural_stop_bar_close_exact_time_and_price(tmp_path):
    plan = make_exit_plan(
        structural=StructuralStop(
            level=Level(kind="underlying", price=24400.0), trigger="bar_close"
        )
    )
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, plan)
    clock.advance_to(NOW.replace(hour=10, minute=15))
    # tick beyond the level must not fire (bar_close trigger)
    pm.on_market(
        envelope(
            "TICK",
            clock.now(),
            {
                "instrument_id": INST,
                "ltp": 151.10,
                "bid": 151.00,
                "ask": 151.20,
                "underlying_ltp": 24390.0,
            },
        )
    )
    assert pm.open_book()
    fire_ts = clock.now()
    fired = pm.on_market(_bar(fire_ts, 24390.0, underlying_close=24390.0))
    assert fired and fired[0].reason == "STRUCTURAL_STOP"
    assert fired[0].plan_field == "structural"
    assert clock.now() == fire_ts
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] > 0


def test_atr_stop_fixed_at_fill_exact_time_and_price(tmp_path):
    plan = make_exit_plan(atr=AtrStop(k=1.5, trigger="bar_close"))
    entry_under, atr14 = 24500.0, 20.0
    expect = freeze_atr_level("CE", entry_under, 1.5, atr14)
    assert expect == pytest.approx(24470.0)
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan, fill_ctx={"entry_underlying": entry_under, "atr14": atr14})
    assert row["atr_stop_level"] == pytest.approx(24470.0)
    clock.advance_to(NOW.replace(hour=10, minute=18))
    # a later ATR print must not move the frozen level
    row["atr14"] = 80.0
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 151.00, "ask": 151.20, "ltp": 151.10},
        )
    )
    pm.on_market(_bar(clock.now(), 24480.0, underlying_close=24480.0))
    assert pm.open_book()
    fire_ts = clock.now()
    fired = pm.on_market(_bar(fire_ts, 24470.0, underlying_close=24470.0))
    assert fired and fired[0].reason == "ATR_STOP"
    assert fired[0].plan_field == "atr"
    assert clock.now() == fire_ts
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] > 0


def test_signal_flip_own_opposite_on_bar_close(tmp_path):
    plan = make_exit_plan(signal_flip=SignalFlipExit(on=("own_opposite",), trigger="bar_close"))
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan)
    row["strategy_id"] = "TEST-A"
    clock.advance_to(NOW.replace(hour=10, minute=20))
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 151.00, "ask": 151.20, "ltp": 151.10},
        )
    )
    pm.on_market(
        envelope(
            "SIGNAL",
            clock.now(),
            {"strategy_id": "TEST-A", "side": "PE", "underlying": "NIFTY"},
        )
    )
    assert pm.open_book()  # waits for bar close
    fire_ts = clock.now()
    fired = pm.on_market(_bar(fire_ts, 24500.0, underlying_close=24500.0))
    assert fired and fired[0].reason == "SIGNAL_FLIP"
    assert fired[0].plan_field == "signal_flip"
    assert clock.now() == fire_ts
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] > 0


def test_signal_flip_boss_opposite_on_bar_close(tmp_path):
    plan = make_exit_plan(signal_flip=SignalFlipExit(on=("boss_opposite",), trigger="bar_close"))
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, plan)
    clock.advance_to(NOW.replace(hour=10, minute=22))
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 151.00, "ask": 151.20, "ltp": 151.10},
        )
    )
    pm.on_market(
        envelope(
            "DECISION",
            clock.now(),
            {
                "decision": "ENTER",
                "underlying": "NIFTY",
                "side": "PE",
                "instrument_id": PE_INST,
            },
        )
    )
    assert pm.open_book()
    fire_ts = clock.now()
    fired = pm.on_market(_bar(fire_ts, 24510.0, underlying_close=24510.0))
    assert fired and fired[0].reason == "SIGNAL_FLIP"
    assert not pm.open_book()
    assert pm.store.closed[-1]["last_exit_price"] > 0


def test_evaluate_table_structural_atr_flip_exact():
    """Pure evaluate table: exact reason, field, and no fire on the wrong event."""
    fill = datetime(2026, 9, 28, 10, 1, tzinfo=IST)
    structural = make_exit_plan(
        structural=StructuralStop(level=Level(kind="underlying", price=24400.0))
    )
    pos = {
        "instrument_id": INST,
        "net_qty": 130,
        "orig_qty": 130,
        "avg_price": 151.10,
        "stop_price": 140.0,
        "exit_plan": structural,
        "fill_ts": fill,
        "last_good_quote": 151.10,
    }
    tick = evaluate(
        pos,
        fill + timedelta(minutes=2),
        mark=151.10,
        quote_ts=fill,
        event_kind="TICK",
        underlying=24350.0,
    )
    assert tick is None
    hit = evaluate(
        pos,
        fill + timedelta(minutes=2),
        mark=151.10,
        quote_ts=fill,
        event_kind="BAR_CLOSED",
        underlying=24350.0,
    )
    assert hit is not None
    assert hit.reason == "STRUCTURAL_STOP"
    assert hit.plan_field == "structural"

    atr_plan = make_exit_plan(atr=AtrStop(k=2.0, trigger="bar_close"))
    atr_pos = dict(pos)
    atr_pos["exit_plan"] = atr_plan
    freeze_fill_levels(atr_pos, atr_plan, 151.10, 130, entry_underlying=24500.0, atr14=10.0)
    assert atr_pos["atr_stop_level"] == pytest.approx(24480.0)
    miss = evaluate(
        atr_pos,
        fill + timedelta(minutes=3),
        mark=151.10,
        quote_ts=fill,
        event_kind="BAR_CLOSED",
        underlying=24490.0,
    )
    assert miss is None
    atr_hit = evaluate(
        atr_pos,
        fill + timedelta(minutes=3),
        mark=151.10,
        quote_ts=fill,
        event_kind="BAR_CLOSED",
        underlying=24480.0,
    )
    assert atr_hit is not None and atr_hit.reason == "ATR_STOP"

    flip_plan = make_exit_plan(signal_flip=SignalFlipExit(on=("own_opposite", "boss_opposite")))
    flip_pos = dict(pos)
    flip_pos["exit_plan"] = flip_plan
    assert (
        evaluate(
            flip_pos,
            fill + timedelta(minutes=4),
            mark=151.10,
            quote_ts=fill,
            event_kind="BAR_CLOSED",
            own_opposite=True,
        ).reason
        == "SIGNAL_FLIP"
    )
    flip_pos.pop("flip_pending", None)
    assert (
        evaluate(
            flip_pos,
            fill + timedelta(minutes=4),
            mark=151.10,
            quote_ts=fill,
            event_kind="BAR_CLOSED",
            boss_opposite=True,
        ).reason
        == "SIGNAL_FLIP"
    )


def test_grace_is_not_required_on_v2_09_plans(tmp_path):
    """V2-09 plans without grace still fire time/target; safeguards stay on."""
    from contracts.payloads import TimeStop

    plan = make_exit_plan(time_stops=(TimeStop(after_s=5, when="always"),))
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan)
    clock.advance_to(row["fill_ts"] + timedelta(seconds=5))
    fired = pm.on_market(envelope("CLOCK", clock.now(), {"minute": "10:01"}))
    assert fired and fired[0].reason == "TIME_EXIT"
    clock.advance_by(timedelta(milliseconds=200))
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 150.00, "ask": 150.20, "ltp": 150.10},
        )
    )
    assert not pm.open_book()
    pm.assert_stop_invariant()


def test_house_stop_premium_snaps_up_to_tick_grid() -> None:
    """Long stop snaps up onto the 0.05 grid so loss stays <= ₹30k."""
    px = house_stop_premium(500, 65, 30000)
    assert px == pytest.approx(38.50)
    assert abs(round(px / 0.05) * 0.05 - px) < 1e-9
    assert 65 * (500.0 - px) <= 30000.0 + 1e-9


def test_house_stop_premium_tiny_caps_clamped() -> None:
    """Tiny / nonsensical risk caps: >= one tick, never below 0, never above entry."""
    tick = 0.05
    cases = (
        (100.0, 65, 1.0),  # ₹1 cap on one NIFTY lot
        (100.03, 65, 0.0),  # zero cap, off-grid entry (snap-up must not pass entry)
        (100.0, 65, -500.0),  # negative cap
        (0.10, 65, 30_000.0),  # house cap vs tiny premium
        (0.03, 65, 1.0),  # entry below one tick
    )
    for entry, qty, cap in cases:
        px = house_stop_premium(entry, qty, cap)
        assert px >= 0.0
        assert px <= entry + 1e-12
        if entry >= tick:
            assert px >= tick - 1e-12
        assert abs(round(px / tick) * tick - px) < 1e-9 or px == pytest.approx(entry)


def test_evaluate_founder_kill_names_kill_switch() -> None:
    plan = make_exit_plan()
    req = evaluate(
        {
            "instrument_id": INST,
            "net_qty": 130,
            "orig_qty": 130,
            "avg_price": 151.10,
            "stop_price": 140.0,
            "exit_plan": plan,
            "fill_ts": NOW,
            "last_good_quote": 151.10,
        },
        NOW,
        mark=151.10,
        quote_ts=NOW,
        founder_kind="KILL",
    )
    assert req is not None
    assert req.reason == "KILL_SWITCH"
    assert req.plan_field == "kill_switch"
    assert_exit_reason(req, plan)


def test_founder_kill_through_manager_flattens_whole_lots(tmp_path):
    """FOUNDER_COMMAND kind=KILL goes through on_market and SELLs net qty."""
    clock = SimClock(NOW)
    broker = make_broker(clock=clock)
    pm = make_manager(tmp_path, clock, broker=broker)
    row = _enter(pm, clock, make_exit_plan(), lots=2)
    net = int(row["net_qty"])
    assert net == 130
    fired = pm.on_market(
        envelope("FOUNDER_COMMAND", clock.now(), {"kind": "KILL", "instrument_id": INST})
    )
    assert fired and len(fired) == 1
    assert fired[0].reason == "KILL_SWITCH"
    assert fired[0].plan_field == "kill_switch"
    assert fired[0].qty == net
    assert not pm.open_book()
    kills = [o for o in broker.orders.values() if (o.intent.exit_reason or "") == "KILL_SWITCH"]
    assert len(kills) == 1
    assert kills[0].intent.qty == net
    assert pm.store.closed[-1]["exit_reason"] == "KILL_SWITCH"
    pm.assert_stop_invariant()


def test_exit_reason_mismatch_never_blocks_flatten(tmp_path, monkeypatch, caplog):
    """A REG-18a field mismatch logs CRITICAL and still flattens."""
    import logging

    import oms.positions as positions_mod

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, make_exit_plan(), lots=2)
    real = positions_mod.evaluate

    def mismatched(*args, **kwargs):
        req = real(*args, **kwargs)
        if req is None:
            return None
        return ExitRequest(
            req.reason,
            "structural",
            req.qty,
            stale_quote=req.stale_quote,
            price_hint=req.price_hint,
        )

    monkeypatch.setattr(positions_mod, "evaluate", mismatched)
    caplog.set_level(logging.CRITICAL)
    fired = pm.on_market(
        envelope("FOUNDER_COMMAND", clock.now(), {"kind": "CUT_LOSS", "instrument_id": INST})
    )
    assert fired
    assert not pm.open_book()
    assert any(a["reason_code"] == "REG_18A_MISMATCH" for a in pm.alerts)
    assert "REG-18a" in caplog.text
    assert "flattening anyway" in caplog.text
    pm.assert_stop_invariant()
