"""V2-08b planner acceptance. One test per bullet. Paper / fixtures only."""

from __future__ import annotations

import time
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from brokers.fills import TICK, Quote
from contracts.clock import SimClock
from helpers import INST, NOW, REPO, SIG, make_decision, make_router
from risk_engine.last_good import ConfigInvalid
from strategies.params_hash import config_hash

from oms import Account, CardPolicy, MemoryLedger, policy_params_hash
from oms.planner import (
    CHASE_LOOKAHEAD_S,
    OrderPlanner,
    Side,
    entry_config_hash,
    load_entry_config,
    marketable_limit,
    snap_ask_up,
)

BAR_CLOSE = NOW - timedelta(seconds=1)


def _cfg(tmp_path: Path, entry_over: dict | None = None, chase_over: dict | None = None):
    entry = yaml.safe_load((REPO / "config/v2/entry_location.yaml").read_text())
    chase = yaml.safe_load((REPO / "config/v2/entry/chase_defaults.yaml").read_text())
    if entry_over:
        entry.update(entry_over)
    if chase_over:
        chase.update(chase_over)
    epath = tmp_path / "entry_location.yaml"
    cpath = tmp_path / "chase_defaults.yaml"
    epath.write_text(yaml.safe_dump(entry))
    cpath.write_text(yaml.safe_dump(chase))
    return load_entry_config(epath, cpath), epath, cpath, entry, chase


def _planner(tmp_path: Path, clock: SimClock, **kw: object) -> OrderPlanner:
    cfg = kw.pop("config", None)
    if cfg is None:
        cfg, _, _, _, _ = _cfg(tmp_path)
    router = make_router(tmp_path, clock, **kw)  # type: ignore[arg-type]
    return OrderPlanner(clock=clock, router=router, config=cfg)  # type: ignore[arg-type]


def _quote(clock: SimClock, ask: float = 151.20, ltp: float | None = 151.10) -> Quote:
    return Quote(available_ts=clock.now(), bid=151.00, ask=ask, ltp=ltp, instrument_id=INST)


def test_default_chase_is_marketable_limit_at_ask_plus_ticks(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock)
    dec = make_decision()
    planner.on_decision(dec, account=Account("founder"), signal_id=SIG, bar_close_ts=BAR_CLOSE)
    planner.on_quote(_quote(clock, ask=151.20))
    clock.advance_by(timedelta(milliseconds=250))
    planner.on_quote(_quote(clock, ask=151.20))
    oid = next(iter(planner.router.broker.orders))
    order = planner.router.broker.orders[oid]
    assert order.intent.order_type == "LIMIT"
    assert order.intent.price == marketable_limit(151.20, 2)
    assert order.intent.price == pytest.approx(151.20 + 2 * TICK)
    assert order.intent.purpose == "ENTRY"
    row = next(iter(planner.store.entry_plans.values()))
    assert row["action"] == "CHASE"
    assert row["status"] == "FILLED"
    assert order.avg_fill_price == order.intent.price  # K17: fill at the limit


def test_no_code_path_emits_a_market_entry_order() -> None:
    src = Path("packages/oms/src/oms/planner.py").read_text(encoding="utf-8")
    assert 'order_type="MARKET"' not in src
    assert "order_type='MARKET'" not in src
    router_src = Path("packages/oms/src/oms/router.py").read_text(encoding="utf-8")
    assert 'order_type="LIMIT"' in router_src
    assert 'purpose="ENTRY"' in router_src
    entry_block = router_src.split("def submit")[1].split("def _place_adopt")[0]
    assert "MARKET" not in entry_block


def test_chase_timeout_cancels_timeout_unfilled_and_records_missed_chase(
    tmp_path: Path,
) -> None:
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock)
    planner.on_decision(
        make_decision(), account=Account("founder"), signal_id=SIG, bar_close_ts=BAR_CLOSE
    )
    planner.on_quote(_quote(clock, ask=151.20))
    order = next(iter(planner.router.broker.orders.values()))
    assert order.intent.order_type == "LIMIT"
    clock.advance_by(timedelta(seconds=2))
    planner.on_clock()
    assert order.state.value == "CANCELLED"
    assert order.cancel_reason == "TIMEOUT_UNFILLED"
    row = next(iter(planner.store.entry_plans.values()))
    assert row["status"] == "MISSED_CHASE"
    assert row["ask_at_cancel"] == 151.20
    clock.advance_by(timedelta(seconds=0.5))
    planner.on_quote(_quote(clock, ask=151.15))
    clock.advance_by(timedelta(seconds=CHASE_LOOKAHEAD_S))
    planner.on_clock()
    result = row["result"]
    assert result.status == "MISSED_CHASE"
    assert result.shadow["ask_at_cancel"] == 151.20
    assert result.shadow["first_fillable_ask_5s"] == 151.15
    assert result.shadow["chase_price"] == 151.15
    assert "pnl_pts" in result.shadow


def test_per_card_override_is_honoured_and_changes_params_hash(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock)
    override = CardPolicy(max_chase_ticks=4, chase_timeout_s=1.0)
    planner.on_decision(
        make_decision(),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=BAR_CLOSE,
        policy=override,
    )
    planner.on_quote(_quote(clock, ask=151.20))
    order = next(iter(planner.router.broker.orders.values()))
    assert order.intent.price == marketable_limit(151.20, 4)
    default = CardPolicy()
    chase_hash = planner.config.chase_hash
    assert policy_params_hash(override, chase_hash) != policy_params_hash(default, chase_hash)


def test_pullback_limit_missed_and_trade_through(tmp_path: Path) -> None:
    cfg, _, _, _, _ = _cfg(
        tmp_path,
        entry_over={"pullback_limit": {"enabled": True, "limit_timeout_s": 3.0}},
    )
    clock = SimClock(NOW)
    filled = _planner(tmp_path, clock, config=cfg)
    filled.on_decision(
        make_decision(),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=BAR_CLOSE,
        policy=CardPolicy(mode="pullback_limit"),
        zone_price=144.10,
    )
    filled.on_quote(_quote(clock, ask=151.20, ltp=151.10))
    clock.advance_by(timedelta(milliseconds=200))
    filled.on_quote(Quote(clock.now(), 144.10, 144.20, 144.10, INST))  # touch, no fill
    order = next(iter(filled.router.broker.orders.values()))
    assert order.state.value != "FILLED"
    clock.advance_by(timedelta(milliseconds=200))
    filled.on_quote(Quote(clock.now(), 143.90, 144.00, 144.00, INST))  # through
    assert order.state.value == "FILLED"
    assert order.avg_fill_price == 144.10

    clock2 = SimClock(NOW)
    missed = _planner(tmp_path, clock2, config=cfg, store=MemoryLedger())
    missed.on_decision(
        make_decision(decision_id="dc_miss"),
        account=Account("founder"),
        signal_id="sg_miss",
        bar_close_ts=BAR_CLOSE,
        policy=CardPolicy(mode="pullback_limit"),
        zone_price=144.10,
    )
    missed.on_quote(_quote(clock2, ask=151.20))
    clock2.advance_by(timedelta(seconds=3))
    missed.on_clock()
    row = next(iter(missed.store.entry_plans.values()))
    assert row["status"] == "MISSED"
    assert row["result"].shadow["CHASE"]["fill_price"] == 151.20


def test_wait_consolidation_expiry_is_missed(tmp_path: Path) -> None:
    cfg, _, _, _, _ = _cfg(
        tmp_path,
        entry_over={
            "wait_consolidation": {
                "enabled": True,
                "consol_max_atr": 0.4,
                "wait_max_bars": 2,
            }
        },
    )
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock, config=cfg)
    planner.on_decision(
        make_decision(),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=BAR_CLOSE,
        policy=CardPolicy(mode="wait_consolidation"),
    )
    planner.on_bar_close()
    planner.on_clock()
    row = next(iter(planner.store.entry_plans.values()))
    assert row["status"] == "PENDING"
    planner.on_bar_close()
    planner.on_clock()
    assert row["status"] == "MISSED"
    assert planner.router.broker.orders == {}


def test_planner_plus_features_under_5ms_p99(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock)
    dec = make_decision()
    samples: list[float] = []
    for i in range(80):
        t0 = time.perf_counter()
        planner.on_decision(
            dec,
            account=Account("founder"),
            signal_id=SIG if i == 0 else f"sg_{i}",
            bar_close_ts=BAR_CLOSE,
        )
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    p99 = samples[int(0.99 * (len(samples) - 1))]
    assert p99 < 5.0, p99


def test_risk_rechecked_at_send_and_one_entry_per_signal(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock)
    before = len(planner.router.store.decisions)
    planner.on_decision(
        make_decision(), account=Account("founder"), signal_id=SIG, bar_close_ts=BAR_CLOSE
    )
    planner.on_decision(
        make_decision(), account=Account("founder"), signal_id=SIG, bar_close_ts=BAR_CLOSE
    )
    assert len(planner.store.entry_plans) == 1
    assert len(planner.router.store.decisions) == before
    planner.on_quote(_quote(clock, ask=151.20))
    assert len(planner.router.store.decisions) >= before + 1
    planner.on_quote(_quote(clock, ask=151.20))
    entries = [o for o in planner.router.broker.orders.values() if o.intent.purpose == "ENTRY"]
    assert len(entries) == 1


def test_reg_07_bad_entry_config_keeps_last_good(tmp_path: Path) -> None:
    cfg, epath, _, good, _ = _cfg(tmp_path)
    assert cfg.get()["boss_stretch"] == "record_only"
    last = dict(cfg.get())
    bad = dict(good)
    bad["boss_stretch"] = "veto"
    epath.write_text(yaml.safe_dump(bad))
    with pytest.raises(ConfigInvalid, match="CONFIG_INVALID"):
        cfg.reload()
    assert cfg.get() == last
    null_mode = dict(good)
    null_mode["pullback_limit"] = {"enabled": True, "limit_timeout_s": None}
    epath.write_text(yaml.safe_dump(null_mode))
    with pytest.raises(ConfigInvalid, match="null parameter"):
        cfg.reload()
    assert cfg.get() == last


def test_reg_13_entry_location_config_hash_changes(tmp_path: Path) -> None:
    _, _, _, entry, chase = _cfg(tmp_path)
    base = entry_config_hash(entry, chase)
    changed = dict(entry)
    changed["zones"] = ["fvg"]
    assert entry_config_hash(changed, chase) != base
    chase2 = dict(chase)
    chase2["max_chase_ticks"] = 3
    assert entry_config_hash(entry, chase2) != base
    assert config_hash(entry_location=entry, chase_defaults=chase) != config_hash(
        entry_location=changed, chase_defaults=chase
    )


def test_off_tick_ask_is_snapped_to_0_05_and_not_above_cap() -> None:
    ask = 151.23
    got = marketable_limit(ask, 2)
    snapped = float(snap_ask_up(ask))
    assert snapped == pytest.approx(151.25)
    cap = snapped + 2 * 0.05
    assert got == pytest.approx(cap)
    assert got == pytest.approx(151.35)
    assert got <= cap
    units = Decimal(str(got)) / Decimal("0.05")
    assert units == units.to_integral_value()
    on_tick = (Decimal(str(got)) % Decimal("0.05")) == 0
    assert on_tick, f"marketable_limit({ask})={got} is not a 0.05 tick"


def test_bad_lot_size_must_not_send(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock)
    planner.on_decision(
        make_decision(lots=1, lot_size=10),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=BAR_CLOSE,
    )
    planner.on_quote(_quote(clock, ask=151.20))
    assert planner.router.broker.orders == {}
    row = next(iter(planner.store.entry_plans.values()))
    assert row["status"] == "VETOED"
    assert row["veto"] == "LOT_SIZE_MISMATCH"


def test_veto_is_persisted_on_the_plan_row(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock)
    planner.on_decision(
        make_decision(lots=99),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=BAR_CLOSE,
    )
    planner.on_quote(_quote(clock, ask=151.20))
    assert planner.router.broker.orders == {}
    row = next(iter(planner.store.entry_plans.values()))
    assert row["status"] == "VETOED"
    assert row["veto"] == "MAX_LOTS"


def test_live_and_quotes_are_bounded(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock)
    planner.on_decision(
        make_decision(), account=Account("founder"), signal_id=SIG, bar_close_ts=BAR_CLOSE
    )
    planner.on_quote(_quote(clock, ask=151.20))
    for _ in range(20):
        clock.advance_by(timedelta(milliseconds=40))
        planner.on_quote(_quote(clock, ask=200.00, ltp=200.00))
    live = list(planner._live.values())
    assert live
    assert len(live[0]["quotes"]) <= 2
    stored = next(iter(planner.store.entry_plans.values()))
    assert "quotes" not in stored
    clock.advance_by(timedelta(seconds=2))
    planner.on_clock()
    clock.advance_by(timedelta(seconds=CHASE_LOOKAHEAD_S))
    planner.on_clock()
    assert not planner._live


def test_config_paths_resolve_from_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = load_entry_config()
    assert cfg.path.exists()
    assert cfg.get()["boss_stretch"] == "record_only"
    from boss.selector import entry_files_hash, load_engine_config

    load_engine_config()
    assert len(entry_files_hash()) == 16


def test_planner_uses_sqlite_ledger_entry_plans(tmp_path: Path) -> None:
    """V2-10 real ledger already has entry_plans; planner writes there, not a second store."""
    from ledger.v2 import SqliteLedgerStore

    clock = SimClock(NOW)
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True)
    planner = _planner(tmp_path, clock, store=store)
    planner.on_decision(
        make_decision(), account=Account("founder"), signal_id=SIG, bar_close_ts=BAR_CLOSE
    )
    assert len(store.entry_plans) == 1
    pid = next(iter(store.entry_plans))
    assert store.get_plan(pid) is not None
    assert store.pending_plans()[0]["plan_id"] == pid
    revived = OrderPlanner(clock=clock, router=planner.router, config=planner.config, store=store)
    revived.rebuild()
    assert pid in revived._live


def test_sqlite_process_restart_rebuild_then_timeout_no_duplicate(tmp_path: Path) -> None:
    """Close the sqlite file, reopen a new store+planner, rebuild, drive to TIMEOUT."""
    from ledger.v2 import SqliteLedgerStore

    db = tmp_path / "aad.sqlite"
    clock = SimClock(NOW)
    store = SqliteLedgerStore(db, migrate_schema=True)
    planner = _planner(tmp_path, clock, store=store)
    planner.on_decision(
        make_decision(), account=Account("founder"), signal_id=SIG, bar_close_ts=BAR_CLOSE
    )
    planner.on_quote(_quote(clock, ask=151.20))
    pid = next(iter(store.entry_plans))
    assert store.get_plan(pid)["status"] == "WORKING"
    assert len(planner.router.broker.orders) == 1
    store.close()

    clock2 = SimClock(clock.now())
    store2 = SqliteLedgerStore(db)
    revived = OrderPlanner(
        clock=clock2,
        router=make_router(tmp_path, clock2, store=store2),
        config=planner.config,
        store=store2,
    )
    revived.rebuild()
    live = revived._live[pid]
    assert isinstance(live["policy"], CardPolicy)
    assert live["policy"].chase_timeout_s == 2.0
    assert isinstance(live["bar_close_ts"], type(BAR_CLOSE))
    assert live["bar_close_ts"].tzinfo is not None
    clock2.advance_by(timedelta(seconds=2))
    revived.on_clock()
    assert store2.get_plan(pid)["status"] == "MISSED_CHASE"
    assert len(store2.entry_plans) == 1
    assert revived.router.broker.orders == {}
    store2.close()


def test_memory_upsert_plan_keeps_created_at_and_identity() -> None:
    store = MemoryLedger()
    created = NOW
    store.upsert_plan(
        {
            "plan_id": "mem-1",
            "decision_id": "dec-orig",
            "signal_id": "sig-orig",
            "mode": "chase",
            "action": "CHASE",
            "status": "PENDING",
            "created_at": created,
            "side": Side.BUY,
        }
    )
    store.upsert_plan(
        {
            "plan_id": "mem-1",
            "decision_id": "dec-hacked",
            "signal_id": "sig-hacked",
            "mode": "wait_consolidation",
            "action": "WAIT",
            "created_at": created + timedelta(hours=1),
            "status": "WORKING",
            "client_order_id": "aad1",
        }
    )
    got = store.get_plan("mem-1")
    assert got is not None
    assert got["created_at"] is created
    assert got["decision_id"] == "dec-orig"
    assert got["signal_id"] == "sig-orig"
    assert got["mode"] == "chase"
    assert got["action"] == "CHASE"
    assert got["status"] == "WORKING"
    assert got["client_order_id"] == "aad1"


def test_stretch_has_no_catastrophic_price(tmp_path: Path) -> None:
    src = (REPO / "packages/oms/src/oms/planner.py").read_text(encoding="utf-8")
    assert "catastrophic_price" not in src
    clock = SimClock(NOW)
    planner = _planner(tmp_path, clock)
    planner.on_decision(
        make_decision(
            stretch={"record_only": True, "zone_atr": 1.6, "ema20_atr": 2.4, "twap_atr": 3.1}
        ),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=BAR_CLOSE,
    )
    planner.on_quote(_quote(clock, ask=151.20))
    order = next(iter(planner.router.broker.orders.values()))
    assert order.intent.stop_loss is not None
    assert order.intent.stop_loss < float(order.intent.price or 0)
    assert order.intent.stop_loss != pytest.approx(float(order.intent.price or 0) - 1.0)
    assert "catastrophic_price" not in (order.intent.__dict__)
