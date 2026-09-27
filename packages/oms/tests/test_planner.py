"""V2-08b order planner acceptance. One test per build-plan bullet. Paper only."""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml
from brokers.fills import ClockedPaperBroker
from contracts.clock import IST, SimClock
from events.bus import MemoryBus
from helpers import (
    NOW,
    SIG,
    SpyBroker,
    make_decision,
    make_router,
    quote_at,
    write_entry_cfg,
    write_risk_cfg,
)
from risk_engine import V2RiskEngine
from risk_engine.last_good import ConfigInvalid

from oms import MemoryLedger
from oms.planner import (
    ENTRY_ORDER_TYPE,
    REPO_CHASE_YAML,
    REPO_ENTRY_YAML,
    CardPolicy,
    EntryConfigStore,
    OrderPlanner,
    load_chase_defaults,
    load_entry_location,
    marketable_limit,
    policy_params_hash,
    resolve_policy,
)

PLANNER_SRC = Path(__file__).resolve().parents[1] / "src" / "oms" / "planner.py"


def _planner(
    tmp_path: Path,
    clock: SimClock,
    *,
    broker: ClockedPaperBroker | None = None,
    entry_path: Path | None = None,
    card: CardPolicy | None = None,
) -> tuple[OrderPlanner, ClockedPaperBroker]:
    del card
    brk = broker if broker is not None else ClockedPaperBroker(clock=clock)
    router = make_router(tmp_path, clock, broker=brk)
    store = EntryConfigStore(entry_path or REPO_ENTRY_YAML, chase_path=REPO_CHASE_YAML)
    planner = OrderPlanner(clock=clock, router=router, config_store=store)
    return planner, brk


def test_default_marketable_limit_never_market(tmp_path: Path) -> None:
    """Default config: one marketable limit at ask + max_chase_ticks; no MARKET entry."""
    clock = SimClock(NOW)
    planner, broker = _planner(tmp_path, clock)
    ask = 151.35
    dec = make_decision()
    plan = planner.accept(dec, bar_close_ts=NOW - timedelta(seconds=1))
    assert plan is not None
    assert plan.action == "CHASE"
    assert ENTRY_ORDER_TYPE == "LIMIT"
    planner.on_quote(quote_at(NOW, ask))
    order = broker.orders.get(plan.client_order_id)
    assert order is not None
    assert order.intent.order_type == "LIMIT"
    assert order.intent.price == marketable_limit(ask, 2)
    assert order.intent.purpose == "ENTRY"
    src = PLANNER_SRC.read_text(encoding="utf-8")
    assert re.search(r'order_type\s*=\s*["\']MARKET["\']', src) is None
    assert "MARKET" not in ENTRY_ORDER_TYPE


def test_chase_timeout_missed_chase_and_card_override_params_hash(tmp_path: Path) -> None:
    """Unfilled chase -> TIMEOUT_UNFILLED / MISSED_CHASE; per-card override changes params_hash."""
    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    planner, _ = _planner(tmp_path, clock, broker=spy)
    cfg = load_entry_location()
    default = resolve_policy(cfg)
    override = resolve_policy(cfg, CardPolicy(max_chase_ticks=5, chase_timeout_s=4.0))
    assert override.max_chase_ticks == 5
    assert override.chase_timeout_s == 4.0
    assert override.params_hash != default.params_hash
    assert override.params_hash == policy_params_hash(
        max_chase_ticks=5,
        chase_timeout_s=4.0,
        chase_calibration=cfg.chase.calibration,
        mode="chase",
    )

    plan = planner.accept(
        make_decision(),
        card=CardPolicy(max_chase_ticks=5, chase_timeout_s=4.0),
        bar_close_ts=NOW - timedelta(seconds=1),
    )
    assert plan is not None
    ask = 151.35
    planner.on_quote(quote_at(NOW, ask))
    live = planner.plan(plan.signal_id)
    assert live is not None
    assert live.plan.limit_price == marketable_limit(ask, 5)
    assert spy.place_calls == 1
    clock.advance_by(timedelta(seconds=4.0))
    results = planner.on_clock()
    assert results and results[0].status == "MISSED_CHASE"
    order = spy.orders[plan.client_order_id]
    assert order.cancel_reason == "TIMEOUT_UNFILLED"
    later = NOW + timedelta(seconds=5)
    clock.advance_to(later)
    planner.on_quote(quote_at(later, 151.80))
    shadow = results[0].shadow or planner.plan(plan.signal_id).result.shadow  # type: ignore[union-attr]
    live = planner.plan(plan.signal_id)
    assert live is not None and live.result is not None
    shadow = live.result.shadow or {}
    assert shadow.get("best_ask_at_cancel") == 151.35
    assert shadow.get("first_fillable_ask_5s") == 151.80
    assert shadow.get("shadow_pnl_pts") is not None


def test_config_invalid_last_good_reg07(tmp_path: Path) -> None:
    """boss_stretch != record_only or enabled+null is refused; last-good stays (REG-07)."""
    path = write_entry_cfg(tmp_path)
    store = EntryConfigStore(path, chase_path=REPO_CHASE_YAML)
    good = store.get()
    path.write_text(
        path.read_text(encoding="utf-8").replace("record_only", "veto"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigInvalid, match="CONFIG_INVALID") as err:
        store.get()
    assert store.last is not None
    assert store.last.config_hash == good.config_hash
    assert "record_only" in str(err.value) or "boss_stretch" in str(err.value)

    bad = write_entry_cfg(
        tmp_path,
        pullback_limit={"enabled": True, "limit_timeout_s": None},
    )
    store2 = EntryConfigStore(bad, chase_path=REPO_CHASE_YAML)
    store2.last = good
    with pytest.raises(ConfigInvalid, match="CONFIG_INVALID"):
        store2.get()
    assert store2.last.config_hash == good.config_hash


def test_pullback_limit_trade_through_reg14(tmp_path: Path) -> None:
    """Enabled pullback: untouched limit -> MISSED + shadow chase; trade-through fills at limit."""
    entry = write_entry_cfg(
        tmp_path,
        default_entry_policy="pullback_limit",
        pullback_limit={"enabled": True, "limit_timeout_s": 30},
    )
    clock = SimClock(NOW)
    miss_broker = SpyBroker(clock=clock)
    planner, _ = _planner(tmp_path, clock, broker=miss_broker, entry_path=entry)
    limit = 144.10
    plan = planner.accept(
        make_decision(limit_price=limit),
        bar_close_ts=NOW - timedelta(seconds=1),
    )
    assert plan is not None and plan.action == "LIMIT"
    planner.on_quote(quote_at(NOW, 151.35, ltp=144.10))
    clock.advance_by(timedelta(seconds=30))
    missed = planner.on_clock()
    assert missed and missed[0].status == "MISSED"
    assert (missed[0].shadow or {}).get("cancel_reason") == "TIMEOUT_UNFILLED"
    assert (missed[0].shadow or {}).get("shadow_chase")

    clock2 = SimClock(NOW)
    fill_broker = ClockedPaperBroker(clock=clock2)
    planner2, _ = _planner(tmp_path, clock2, broker=fill_broker, entry_path=entry)
    plan2 = planner2.accept(
        make_decision(signal_ids=["sg_through"], limit_price=limit),
        bar_close_ts=NOW - timedelta(seconds=1),
    )
    assert plan2 is not None
    planner2.on_quote(quote_at(NOW, 151.35, ltp=151.35))
    through_ts = NOW + timedelta(seconds=1)
    clock2.advance_to(through_ts)
    planner2.on_quote(quote_at(through_ts, 144.00, bid=143.90, ltp=144.00))
    live = planner2.plan(plan2.signal_id)
    assert live is not None
    assert live.status == "FILLED"
    assert live.fill_price == limit


def test_wait_consolidation_expiry_missed(tmp_path: Path) -> None:
    """Enabled wait_consolidation: expiry after wait_max_bars is MISSED."""
    entry = write_entry_cfg(
        tmp_path,
        default_entry_policy="wait_consolidation",
        wait_consolidation={"enabled": True, "consol_max_atr": 1.0, "wait_max_bars": 2},
    )
    clock = SimClock(NOW)
    planner, broker = _planner(tmp_path, clock, entry_path=entry)
    plan = planner.accept(make_decision(), bar_close_ts=NOW)
    assert plan is not None and plan.action == "WAIT"
    first = planner.on_bar()
    assert first == []
    expired = planner.on_bar()
    assert expired and expired[0].status == "MISSED"
    assert broker.orders == {}


def test_restart_pending_limit_no_duplicate_reg04(tmp_path: Path) -> None:
    """kill -9 with a pending limit: plan rebuilt, never a second order (REG-04)."""
    entry = write_entry_cfg(
        tmp_path,
        default_entry_policy="pullback_limit",
        pullback_limit={"enabled": True, "limit_timeout_s": 60},
    )
    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    router = make_router(tmp_path, clock, broker=spy)
    store = router.store
    cfg_store = EntryConfigStore(entry, chase_path=REPO_CHASE_YAML)
    planner = OrderPlanner(clock=clock, router=router, store=store, config_store=cfg_store)
    plan = planner.accept(make_decision(limit_price=144.10), bar_close_ts=NOW - timedelta(seconds=1))
    assert plan is not None
    planner.on_quote(quote_at(NOW, 151.35, ltp=151.35))
    assert spy.place_calls == 1
    assert planner.plan(plan.signal_id) is not None
    assert planner.plan(plan.signal_id).status == "SENT"  # type: ignore[union-attr]

    spy2 = SpyBroker(clock=clock)
    router2 = make_router(tmp_path, clock, broker=spy2, store=store)
    revived = OrderPlanner(clock=clock, router=router2, store=store, config_store=cfg_store)
    assert revived.rebuild() == 1
    again = revived.accept(make_decision(limit_price=144.10), bar_close_ts=NOW)
    assert again is not None and again.plan_id == plan.plan_id
    revived.on_quote(quote_at(NOW, 151.40))
    revived.on_clock()
    assert spy2.place_calls == 0
    assert len(store.pending_plans()) == 1


def test_entry_location_config_hash_reg13(tmp_path: Path) -> None:
    """Changing any entry-location or chase-default value changes config_hash (REG-13)."""
    base = load_entry_location()
    changed = write_entry_cfg(tmp_path, zones=["fvg"])
    other = load_entry_location(changed)
    assert other.config_hash != base.config_hash
    chase = tmp_path / "chase_defaults.yaml"
    raw = yaml.safe_load(REPO_CHASE_YAML.read_text(encoding="utf-8"))
    raw["max_chase_ticks"] = 3
    chase.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with_chase = load_entry_location(REPO_ENTRY_YAML, chase_path=chase)
    assert with_chase.config_hash != base.config_hash
    assert with_chase.chase.max_chase_ticks == 3
    assert load_chase_defaults().max_chase_ticks == 2


def test_planner_features_p99_under_5ms(tmp_path: Path) -> None:
    """Planner + stretch/location features < 5 ms p99 per decision."""
    from datetime import timedelta as _td

    from marketdata.types import BarClosed

    from boss.selector import record_stretch
    from indicators.location import compute_entry_location

    cfg = load_entry_location()
    policy = resolve_policy(cfg)
    loc = {
        "signal_candle_atr": 2.4,
        "entry_distance_atr": 1.6,
        "atr": 6.8,
        "nearest": {"zone": "fvg", "price": 24501.5, "distance_atr": 1.6, "source": "1m"},
        "zones": [
            {"zone": "fvg", "price": 24501.5, "distance_atr": 1.6, "source": "1m"},
            {"zone": "ema20", "price": 24496.0, "distance_atr": 2.4, "source": "1m"},
            {"zone": "vwap", "price": 24488.9, "distance_atr": 3.1, "source": "twap"},
        ],
    }
    base = datetime(2026, 1, 2, 9, 15, tzinfo=IST)
    bars = []
    px = 24500.0
    for i in range(20):
        start = base + _td(minutes=i)
        end = start + _td(minutes=1)
        bars.append(
            BarClosed(
                instrument_id="NIFTY",
                tf="1m",
                start=start.isoformat(),
                end=end.isoformat(),
                o=px,
                h=px + 8,
                l=px - 4,
                c=px + 2,
                v=1000,
                n_ticks=60,
                available_ts=(end + _td(seconds=1)).isoformat(),
            )
        )
        px += 1.0
    samples: list[float] = []
    for _ in range(200):
        t0 = time.perf_counter()
        compute_entry_location(bars, side="CE")
        record_stretch(loc, cfg.config_hash)
        resolve_policy(cfg, CardPolicy(max_chase_ticks=2))
        marketable_limit(151.35, policy.max_chase_ticks, policy.tick_size)
        samples.append((time.perf_counter() - t0) * 1000.0)
    samples.sort()
    p99 = samples[int(len(samples) * 0.99) - 1]
    assert p99 < 5.0, f"planner+features p99 {p99:.3f} ms"


def test_risk_rechecked_at_send_and_one_entry_per_signal(tmp_path: Path) -> None:
    """Risk is re-checked at send time; one entry order per signal."""
    clock = SimClock(NOW)
    cfg_path = write_risk_cfg(tmp_path)
    spy = SpyBroker(clock=clock)
    store = MemoryLedger()
    from oms.router import OrderRouter

    bus = MemoryBus()
    risk = V2RiskEngine(ledger=store, config_path=cfg_path, bus=bus)
    router = OrderRouter(clock=clock, risk=risk, broker=spy, store=store, bus=bus)
    planner = OrderPlanner(
        clock=clock,
        router=router,
        store=store,
        config_store=EntryConfigStore(REPO_ENTRY_YAML, chase_path=REPO_CHASE_YAML),
    )
    dec = make_decision()
    a = planner.accept(dec, bar_close_ts=NOW - timedelta(seconds=1))
    b = planner.accept(dec, bar_close_ts=NOW - timedelta(seconds=1))
    assert a is not None and b is not None and a.plan_id == b.plan_id
    Path(str(yaml.safe_load(cfg_path.read_text())["kill_switch_file"])).write_text("on")
    planner.on_quote(quote_at(NOW, 151.35))
    assert spy.place_calls == 0
    live = planner.plan(SIG)
    assert live is not None
    assert live.result is not None
    assert live.result.status == "CANCELLED"

    clock2 = SimClock(NOW)
    spy2 = SpyBroker(clock=clock2)
    planner2, _ = _planner(tmp_path, clock2, broker=spy2)
    planner2.accept(make_decision(), bar_close_ts=NOW - timedelta(seconds=1))
    planner2.accept(make_decision(), bar_close_ts=NOW - timedelta(seconds=1))
    planner2.on_quote(quote_at(NOW, 151.35))
    assert spy2.place_calls == 1
    assert spy2.types == ["LIMIT"]
