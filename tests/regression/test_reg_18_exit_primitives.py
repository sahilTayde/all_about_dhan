"""REG-18a-e and V2-09b inherit / grep acceptance."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from contracts.payloads import (
    AtrStop,
    CatastrophicStop,
    GracePeriod,
    Level,
    SignalFlipExit,
    StructuralStop,
    TimeStop,
)
from helpers import INST, NOW, depth_env, envelope, make_decision, make_exit_plan, make_manager, make_plan
from risk_engine import IST
from strategies.params_hash import (
    ExitPlanLoadError,
    inherit_exit_defaults,
    load_exit_defaults,
    resolve_exit_plan,
)

from oms import Account, Veto, load_exit_defaults as oms_load_defaults
from oms.exits import (
    ALLOWED_REASONS,
    HOUSE_MAX_LOSS_INR,
    assert_exit_reason,
    evaluate,
    house_stop_premium,
    plan_from_mapping,
)

REPO = Path(__file__).resolve().parents[2]
DEFAULTS = REPO / "config" / "v2" / "exits" / "defaults.yaml"
OMS_SRC = REPO / "packages" / "oms"
STRAT_SRC = REPO / "packages" / "strategies"
LEGACY_CANCELS = (
    "CANCEL_AGAINST",
    "CANCEL_ADVERSE",
    "CANCEL_STALL",
    "COVER_LONG_UNWIND",
)


def _enter(pm, clock, plan, lots=2, *, fill_ctx=None):
    if fill_ctx:
        from contracts.ids import order_id
        from helpers import SIG

        pm.remember_fill_context(order_id("founder", SIG, "entry"), **fill_ctx)
    out = pm.router.submit(
        make_plan(), make_decision(lots=lots), Account("founder"), exit_plan=plan
    )
    assert not isinstance(out, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    pm.router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
    )
    return pm.open_book()[0]


def test_reg_18a_every_exit_names_plan_field(tmp_path):
    """REG-18a: every exit on every fixture has an allowed reason naming the plan field."""
    fixtures: list[tuple[str, object]] = []

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, make_exit_plan())
    clock.advance_to(NOW.replace(hour=10, minute=30))
    fired = pm.on_market(
        envelope("FOUNDER_COMMAND", clock.now(), {"kind": "CUT_LOSS", "instrument_id": INST})
    )
    fixtures.append(("FOUNDER_COMMAND", fired[0] if fired else None))

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(pm, clock, make_exit_plan())
    clock.advance_to(NOW.replace(hour=10, minute=31))
    pm.on_market(
        envelope("TICK", clock.now(), {"instrument_id": INST, "ltp": 139.90, "bid": 139.80, "ask": 140.00})
    )
    closed = pm.store.closed[-1]
    fixtures.append(("CATASTROPHIC_STOP", closed.get("exit_reason")))

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    plan = make_exit_plan(
        structural=StructuralStop(level=Level(kind="underlying", price=24400.0))
    )
    _enter(pm, clock, plan)
    clock.advance_to(NOW.replace(hour=10, minute=32))
    fired = pm.on_market(
        envelope(
            "BAR_CLOSED",
            clock.now(),
            {
                "instrument_id": "NSE_IDX:NIFTY",
                "c": 24390.0,
                "underlying_close": 24390.0,
            },
        )
    )
    fixtures.append(("STRUCTURAL_STOP", fired[0] if fired else None))

    for name, item in fixtures:
        if item is None:
            raise AssertionError(f"REG-18a: {name} did not fire")
        if hasattr(item, "reason"):
            assert item.reason in ALLOWED_REASONS
            assert_exit_reason(item, make_exit_plan() if name != "STRUCTURAL_STOP" else plan)
            assert item.reason == name
        else:
            assert item == name
            assert item in ALLOWED_REASONS


def test_reg_18b_catastrophic_and_time_never_closes_on_plus_minus_5(tmp_path):
    """REG-18b: only catastrophic + time stop; ±5 pt premium wander is not an exit."""
    plan = make_exit_plan(time_stops=(TimeStop(after_s=3600, when="always"),))
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    row = _enter(pm, clock, plan)
    entry = float(row["avg_price"])
    for delta in (-5.0, -4.0, 4.0, 5.0, 0.0, -5.0):
        clock.advance_by(timedelta(seconds=15))
        px = round(entry + delta, 2)
        pm.on_market(depth_env(clock.now(), px, px + 0.20, px))
        assert pm.open_book(), f"closed early at {px} (legacy cancel cluster)"
        assert pm.open_book()[0]["exit_reason"] in (None, "") or "CANCEL" not in str(
            pm.open_book()[0].get("exit_reason")
        )
    clock.advance_to(row["fill_ts"] + timedelta(seconds=3600))
    pm.on_market(envelope("CLOCK", clock.now(), {"minute": "11:01"}))
    clock.advance_by(timedelta(milliseconds=200))
    pm.on_market(depth_env(clock.now(), entry, entry + 0.20, entry))
    assert not pm.open_book()
    assert pm.store.closed[-1]["exit_reason"] == "TIME_EXIT"


def test_reg_18c_grace_blocks_structural_atr_time_flip_not_catastrophic_eod_founder(tmp_path):
    """REG-18c: grace blocks structural/ATR/time/flip; not catastrophic, EOD, founder."""
    grace = GracePeriod(seconds=180)
    fill = NOW

    def _pos(plan, **extra):
        row = {
            "instrument_id": INST,
            "net_qty": 130,
            "orig_qty": 130,
            "avg_price": 151.10,
            "stop_price": 140.0,
            "exit_plan": plan,
            "fill_ts": fill,
            "last_good_quote": 151.10,
            "atr_stop_level": 24470.0,
        }
        row.update(extra)
        return row

    inside = fill + timedelta(seconds=60)
    blocked = (
        make_exit_plan(
            grace=grace,
            structural=StructuralStop(level=Level(kind="underlying", price=24400.0)),
        ),
        "BAR_CLOSED",
        {"underlying": 24300.0},
        "STRUCTURAL_STOP",
    )
    atr_plan = make_exit_plan(grace=grace, atr=AtrStop(k=1.5))
    time_plan = make_exit_plan(grace=grace, time_stops=(TimeStop(after_s=1, when="always"),))
    flip_plan = make_exit_plan(grace=grace, signal_flip=SignalFlipExit(on=("own_opposite",)))

    for plan, kind, kw, _name in (
        blocked,
        (atr_plan, "BAR_CLOSED", {"underlying": 24400.0}, "ATR_STOP"),
        (time_plan, "CLOCK", {}, "TIME_EXIT"),
        (flip_plan, "BAR_CLOSED", {"own_opposite": True}, "SIGNAL_FLIP"),
    ):
        req = evaluate(
            _pos(plan),
            inside,
            mark=151.10,
            quote_ts=fill,
            event_kind=kind,
            **kw,
        )
        assert req is None, f"grace failed to block {_name}"

    cat = evaluate(_pos(make_exit_plan(grace=grace)), inside, mark=139.0, quote_ts=fill)
    assert cat is not None and cat.reason == "CATASTROPHIC_STOP"

    eod = evaluate(
        _pos(make_exit_plan(grace=grace)),
        datetime(2026, 9, 28, 15, 15, tzinfo=IST),
        mark=151.10,
        quote_ts=fill,
        event_kind="CLOCK",
    )
    assert eod is not None and eod.reason == "FLATTEN_EOD"

    founder = evaluate(
        _pos(make_exit_plan(grace=grace)),
        inside,
        mark=151.10,
        quote_ts=fill,
        founder_kind="CUT_LOSS",
    )
    assert founder is not None and founder.reason == "FOUNDER_COMMAND"

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    _enter(
        pm,
        clock,
        make_exit_plan(
            grace=grace,
            structural=StructuralStop(level=Level(kind="underlying", price=24400.0)),
        ),
    )
    clock.advance_by(timedelta(seconds=30))
    pm.on_market(
        envelope(
            "BAR_CLOSED",
            clock.now(),
            {"instrument_id": "NSE_IDX:NIFTY", "c": 24300.0, "underlying_close": 24300.0},
        )
    )
    assert pm.open_book()
    pm.on_market(
        envelope("FOUNDER_COMMAND", clock.now(), {"kind": "CUT_LOSS", "instrument_id": INST})
    )
    assert not pm.open_book()


def test_reg_18d_plan_without_catastrophic_refuses_to_load():
    """REG-18d: a plan without a catastrophic stop refuses to load."""
    with pytest.raises(ValueError, match="catastrophic"):
        plan_from_mapping({"structural": {"level": {"kind": "underlying", "price": 1.0}}})
    with pytest.raises(ExitPlanLoadError, match="REG-18d"):
        resolve_exit_plan({})


def test_reg_18e_editing_defaults_does_not_change_running_plan(tmp_path):
    """REG-18e: editing defaults.yaml does not change a running strategy's resolved plan."""
    native = Level(kind="underlying", price=24400.0)
    running = inherit_exit_defaults(native_invalidation=native, path=DEFAULTS)
    digest = running.defaults_from
    assert digest and digest.startswith("exit_defaults@")
    house = running.catastrophic.level.price
    assert house == HOUSE_MAX_LOSS_INR

    copy = tmp_path / "defaults.yaml"
    copy.write_text(DEFAULTS.read_text().replace("max_loss: 30000", "max_loss: 1000"))
    edited, new_digest = load_exit_defaults(copy)
    assert new_digest != digest.split("@", 1)[1]
    later = inherit_exit_defaults(
        native_invalidation=native, defaults=edited, defaults_sha256=new_digest
    )
    assert later.catastrophic.level.price == 1000.0
    assert later.defaults_from != running.defaults_from
    assert running.catastrophic.level.price == HOUSE_MAX_LOSS_INR
    assert running.defaults_from == digest
    assert running.structural is not None
    assert running.structural.level.price == 24400.0


def test_defaults_all_null_omitted_relied_on_primitive_refuses(tmp_path):
    """With defaults all null, a strategy that omits a primitive it relies on refuses."""
    empty = tmp_path / "empty.yaml"
    empty.write_text(
        "\n".join(
            f"{k}: null"
            for k in (
                "catastrophic",
                "structural",
                "atr",
                "time_stops",
                "grace",
                "signal_flip",
                "target",
                "partials",
                "trail",
            )
        )
        + "\n"
    )
    defaults, digest = load_exit_defaults(empty)
    assert all(defaults[k] is None for k in defaults)
    with pytest.raises(ExitPlanLoadError, match="REG-18d"):
        resolve_exit_plan({}, defaults=defaults, defaults_sha256=digest)
    with pytest.raises(ExitPlanLoadError, match="relies on structural"):
        resolve_exit_plan(
            {"catastrophic": CatastrophicStop(level=Level(kind="premium", price=140.0))},
            defaults=defaults,
            defaults_sha256=digest,
            relies_on=("structural",),
        )


def test_legacy_cancel_reasons_absent_from_oms_and_strategies():
    """Grep-style: legacy cancel reasons never appear in oms or strategies."""
    hits: list[str] = []
    for root in (OMS_SRC, STRAT_SRC):
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".md", ".toml", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for token in LEGACY_CANCELS:
                if token in text:
                    hits.append(f"{path.relative_to(REPO)}:{token}")
    assert hits == []


def test_inherit_defaults_exits_only_native_house_eod_founder_kill(tmp_path):
    """Inherit: only native invalidation, ₹30k house stop, EOD, founder, kill."""
    native = Level(kind="underlying", price=24300.0)
    plan = inherit_exit_defaults(native_invalidation=native, path=DEFAULTS)
    assert plan.atr is None
    assert plan.time_stops == ()
    assert plan.grace is None
    assert plan.signal_flip is None
    assert plan.target is None
    assert plan.partials == ()
    assert plan.trail is None
    assert plan.catastrophic.level.kind == "max_loss_inr"

    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    # Resting SL-M must be the far house stop, not the 1-pt stretch fallback.
    qty = 130
    fill_px = 151.10
    house = house_stop_premium(fill_px, qty)
    row = _enter(pm, clock, plan)
    # Engine stop is the resolved house premium; wander ±5 must not exit.
    row["stop_price"] = house
    entry = float(row["avg_price"])
    for delta in (-5.0, 5.0, -3.0, 2.0, 0.0):
        clock.advance_by(timedelta(seconds=20))
        px = round(entry + delta, 2)
        pm.on_market(depth_env(clock.now(), px, px + 0.20, px))
        assert pm.open_book(), f"inherit fired a hidden exit at {px}"
    # underlying still above native invalidation
    pm.on_market(
        envelope(
            "BAR_CLOSED",
            clock.now(),
            {"instrument_id": "NSE_IDX:NIFTY", "c": 24450.0, "underlying_close": 24450.0},
        )
    )
    assert pm.open_book()
    # native invalidation does fire
    fired = pm.on_market(
        envelope(
            "BAR_CLOSED",
            clock.now(),
            {
                "instrument_id": "NSE_IDX:NIFTY",
                "c": 24290.0,
                "underlying_close": 24290.0,
                "event_id": "e2",
            },
        )
    )
    assert fired and fired[0].reason == "STRUCTURAL_STOP"


def test_strategy_without_native_invalidation_refuses_to_inherit():
    """A strategy with no native invalidation level refuses to inherit."""
    defaults, digest = oms_load_defaults(DEFAULTS)
    with pytest.raises(ExitPlanLoadError, match="native invalidation"):
        resolve_exit_plan({}, defaults=defaults, defaults_sha256=digest)
    with pytest.raises(ExitPlanLoadError, match="native invalidation"):
        inherit_exit_defaults(native_invalidation=None, path=DEFAULTS)  # type: ignore[arg-type]
