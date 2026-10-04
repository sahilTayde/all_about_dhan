"""V2-10 recovery acceptance: READY < 60s, paper rebuild, kill -9, halt, recon."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from brokers.fills import ClockedPaperBroker  # type: ignore[import-untyped]
from brokers.orders import Position  # type: ignore[import-untyped]
from contracts.clock import IST, SimClock
from contracts.envelope import Envelope
from ledger.charges import load_rates
from ledger.v2 import SqliteLedgerStore
from risk_engine import RiskState, TradeIntent, V2RiskEngine  # type: ignore[import-untyped]

from runtime.recovery import FAULT_MATRIX_KILL_POINTS, rebuild_paper_broker, recover
from runtime.sources import EnvelopeSource

REPO = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 9, 28, 10, 5, tzinfo=IST)
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
RATES = load_rates(REPO / "config" / "charges.yaml", by_exchange=True)


def _store(tmp_path: Path) -> SqliteLedgerStore:
    return SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)


def _clock() -> SimClock:
    return SimClock(NOW)


def _seed_fill(store: SqliteLedgerStore, cid: str = "aadseed0000000000000000001", inst: str = INST) -> None:
    store.insert_order(
        {
            "client_order_id": cid,
            "symbol": "NIFTY 24400 CE",
            "instrument_id": inst,
            "side": "BUY",
            "qty": 65,
            "purpose": "ENTRY",
            "state": "SUBMITTED",
            "account_id": "founder",
        }
    )
    store.record_fill(cid, 65, 100.0, ts=NOW, side="BUY", symbol="NIFTY 24400 CE", instrument_id=inst)


def _envelope(seq: int, base: datetime) -> Envelope:
    ts = base + timedelta(minutes=seq)
    return Envelope(
        v=2,
        event_type="CLOCK",
        event_id=f"evt_{seq:04d}",
        stream="md:clock",
        source="test",
        event_ts=ts.isoformat(),
        available_ts=ts.isoformat(),
        timestamp=ts.isoformat(),
        account_id=None,
        correlation_id=None,
        causation_id=None,
        payload={"seq": seq},
    )


def test_restart_to_ready_full_fixture_day_under_60s(tmp_path: Path) -> None:
    store = _store(tmp_path)
    base = datetime(2026, 9, 28, 9, 15, tzinfo=IST)
    envs = [_envelope(i, base) for i in range(375)]
    t0 = time.perf_counter()
    with store.transaction():
        for env in envs:
            store.checkpoint(env)
    _seed_fill(store)
    clock = SimClock(base + timedelta(hours=6, minutes=15))
    broker = ClockedPaperBroker(clock=clock)
    result = recover(store, broker=broker, clock=clock, state_dir=tmp_path, source=EnvelopeSource(envs))
    elapsed = time.perf_counter() - t0
    assert result.status == "READY"
    assert result.elapsed_s < 60
    assert elapsed < 60
    body = (tmp_path / "engine_status.json").read_text()
    assert '"status": "READY"' in body and '"restart": true' in body
    store.close()


def test_paper_broker_rebuilt_from_ledger(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_fill(store)
    clock = _clock()
    broker = ClockedPaperBroker(clock=clock)
    n = rebuild_paper_broker(broker, store)
    assert n >= 1
    assert store.open_positions()[0]["net_qty"] == 65
    assert any(p.net_qty == 65 for p in broker.get_positions())
    n2 = broker.rebuild_from_ledger(store)
    assert n2 >= 1
    store.close()


def test_feed_stale_and_strategy_daily_loss(tmp_path: Path) -> None:
    import yaml  # type: ignore[import-untyped,unused-ignore]

    raw = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())
    raw["kill_switch_file"] = str(tmp_path / "KILL_SWITCH")
    cfg = tmp_path / "risk_limits.yaml"
    cfg.write_text(yaml.safe_dump(raw))
    risk = V2RiskEngine(config_path=cfg)
    intent = TradeIntent(
        symbol="NIFTY 24400 CE",
        side="BUY",
        lots=1,
        lot_size=65,
        decision_price=100.0,
        stop_loss=90.0,
        strategy_id="TEST-CROSS",
    )
    stale = risk.check_entry(intent, now=NOW, state=RiskState(feed_status="STALE"))
    assert stale.reason_code == "FEED_STALE" and not stale.approved
    down = risk.check_entry(intent, now=NOW, state=RiskState(feed_status="DOWN"))
    assert down.reason_code == "FEED_STALE"
    loss = risk.check_entry(intent, now=NOW, state=RiskState(strategy_pnl={"TEST-CROSS": -90000.0}))
    assert loss.reason_code == "STRATEGY_DAILY_LOSS" and not loss.approved


def _kill9(tmp_path: Path, point: str) -> Path:
    db = tmp_path / f"{point}.sqlite"
    marker = tmp_path / f"{point}.marker"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "runtime.fault_worker",
            "--db",
            str(db),
            "--marker",
            str(marker),
            "--crash-at",
            point,
        ],
        cwd=str(REPO),
    )
    for _ in range(200):
        if marker.is_file():
            break
        time.sleep(0.05)
        if proc.poll() is not None:
            raise RuntimeError(f"worker exited early rc={proc.returncode}")
    assert marker.is_file(), "worker never reached crash point"
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait(timeout=5)
    return db


def test_reg_02b_kill_9_between_fill_and_stop(tmp_path: Path) -> None:
    db = _kill9(tmp_path, "after_fill_before_stop")
    store = SqliteLedgerStore(db, rates=RATES)
    clock = _clock()
    broker = ClockedPaperBroker(clock=clock)
    result = recover(store, broker=broker, clock=clock, state_dir=tmp_path)
    assert result.status == "READY"
    assert result.stops_placed >= 1 or any(
        o.intent.purpose == "EXIT" and o.intent.order_type == "SL-M" for o in broker.orders.values()
    )
    for pos in store.open_positions():
        assert store.has_protective(str(pos.get("instrument_id") or pos.get("symbol")))
    cfg = tmp_path / "risk_limits.yaml"
    import yaml  # type: ignore[import-untyped,unused-ignore]

    raw = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())
    raw["kill_switch_file"] = str(tmp_path / "KILL_SWITCH")
    cfg.write_text(yaml.safe_dump(raw))
    risk = V2RiskEngine(ledger=store, config_path=cfg)
    # stop exists before any new entry is considered
    assert store.open_positions()
    d = risk.check_entry(
        TradeIntent(symbol="NIFTY 24400 CE", side="BUY", lots=1, lot_size=65, decision_price=100.0, stop_loss=90.0),
        now=NOW,
    )
    assert d.reason_code != "ENGINE_ERROR"
    store.close()


def test_reg_04a_kill_9_at_each_fault_matrix_point(tmp_path: Path) -> None:
    for point in FAULT_MATRIX_KILL_POINTS:
        db = _kill9(tmp_path / point, point)
        store = SqliteLedgerStore(db, rates=RATES)
        before = {r["instrument_id"]: r["net_qty"] for r in store.positions_v2()}
        assert before, f"no seeded position at {point}"
        clock = _clock()
        broker = ClockedPaperBroker(clock=clock)
        result = recover(store, broker=broker, clock=clock, state_dir=tmp_path / point)
        after = {r["instrument_id"]: r["net_qty"] for r in store.positions_v2()}
        for inst, qty in before.items():
            assert after.get(inst) == qty, f"lost position {inst} at {point}"
        assert result.status == "READY"
        store.close()


def test_reg_04b_broker_only_and_ledger_only_recon_mismatch(tmp_path: Path) -> None:
    from brokers.reconcile import reconcile  # type: ignore[import-untyped]

    store = _store(tmp_path)
    clock = _clock()
    broker = ClockedPaperBroker(clock=clock)
    cfg = tmp_path / "risk_limits.yaml"
    import yaml  # type: ignore[import-untyped,unused-ignore]

    raw = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())
    raw["kill_switch_file"] = str(tmp_path / "KILL_SWITCH")
    cfg.write_text(yaml.safe_dump(raw))
    risk = V2RiskEngine(ledger=store, config_path=cfg)
    intent = TradeIntent(symbol="NIFTY 24400 CE", side="BUY", lots=1, lot_size=65, decision_price=100.0, stop_loss=90.0)
    # recover() rebuilds the paper book from the ledger; plant the mismatch after that
    rebuild_paper_broker(broker, store)
    broker._positions["BROKERONLY"] = Position("NIFTY 25000 PE", 65, 50.0, "BROKERONLY")
    mismatches = reconcile(broker, store, NOW)
    assert any(m.kind == "ORPHAN_BROKER" for m in mismatches)
    d = risk.check_entry(intent, now=NOW)
    assert d.reason_code == "RECON_MISMATCH" and not d.approved
    assert risk.check_exit(
        TradeIntent(symbol="NIFTY 24400 CE", side="SELL", lots=1, lot_size=65, purpose="EXIT", exit_reason="STOP_HIT"),
        now=NOW,
    ).approved

    store2 = SqliteLedgerStore(tmp_path / "led.sqlite", migrate_schema=True, rates=RATES)
    _seed_fill(store2)
    broker2 = ClockedPaperBroker(clock=clock)
    mm2 = reconcile(broker2, store2, NOW)
    assert any(m.kind == "ORPHAN_INTERNAL" for m in mm2)
    snap = store2.risk_snapshot(NOW, 60)
    assert snap["recon_ok"] is False
    d2 = risk.check_entry(intent, now=NOW, state=RiskState(recon_ok=False))
    assert d2.reason_code == "RECON_MISMATCH"
    assert risk.check_exit(
        TradeIntent(symbol="NIFTY 24400 CE", side="SELL", lots=1, lot_size=65, purpose="EXIT", exit_reason="STOP_HIT"),
        now=NOW,
    ).approved
    store.close()
    store2.close()


def test_reg_05e_unreadable_halt_blocks_entries(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.record_halt("2026-09-28", "founder", NOW.isoformat(), "MTM", "{not-json")
    clock = _clock()
    broker = ClockedPaperBroker(clock=clock)
    result = recover(store, broker=broker, clock=clock, state_dir=tmp_path)
    assert result.halt_unreadable is True
    snap = store.risk_snapshot(NOW, 60)
    assert snap["halt_unreadable"] is True
    cfg = tmp_path / "risk_limits.yaml"
    import yaml  # type: ignore[import-untyped,unused-ignore]

    raw = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())
    raw["kill_switch_file"] = str(tmp_path / "KILL_SWITCH")
    cfg.write_text(yaml.safe_dump(raw))
    risk = V2RiskEngine(ledger=store, config_path=cfg)
    d = risk.check_entry(
        TradeIntent(symbol="NIFTY 24400 CE", side="BUY", lots=1, lot_size=65, decision_price=100.0, stop_loss=90.0),
        now=NOW,
    )
    assert d.reason_code == "HALT_UNREADABLE" and not d.approved
    store.close()


def test_reg_05e_forced_closes_rebook_at_saved_time_and_price(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.insert_order(
        {
            "client_order_id": "aadhalt0000000000000000001",
            "symbol": "NIFTY 24400 CE",
            "instrument_id": INST,
            "side": "SELL",
            "qty": 65,
            "purpose": "EXIT",
            "state": "SUBMITTED",
        }
    )
    store.record_halt(
        "2026-09-28",
        "founder",
        NOW.isoformat(),
        "MTM",
        [
            {
                "client_order_id": "aadhalt0000000000000000001",
                "instrument_id": INST,
                "symbol": "NIFTY 24400 CE",
                "qty": 65,
                "price": 88.5,
                "ts": NOW.isoformat(),
                "side": "SELL",
                "account_id": "founder",
            }
        ],
    )
    clock = _clock()
    broker = ClockedPaperBroker(clock=clock)
    recover(store, broker=broker, clock=clock, state_dir=tmp_path)
    fills = list(
        store.conn.execute("SELECT price, ts FROM fills WHERE client_order_id=?", ("aadhalt0000000000000000001",))
    )
    assert fills and float(fills[0][0]) == 88.5
    assert NOW.isoformat()[:19] in str(fills[0][1])
    store.close()
