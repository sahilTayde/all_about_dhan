"""REG-02b, REG-04a/b, REG-05e (V2-10 crash recovery)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
from brokers.fills import ClockedPaperBroker
from brokers.orders import Position
from brokers.reconcile import reconcile
from contracts.clock import IST, SimClock
from ledger.charges import load_rates
from ledger.v2 import SqliteLedgerStore
from risk_engine import RiskState, TradeIntent, V2RiskEngine
from runtime.recovery import FAULT_MATRIX_KILL_POINTS, recover

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 28, 10, 5, tzinfo=IST)
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
RATES = load_rates(REPO / "config" / "charges.yaml", by_exchange=True)


def _risk(tmp_path: Path, store: SqliteLedgerStore) -> V2RiskEngine:
    raw = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())
    raw["kill_switch_file"] = str(tmp_path / "KILL_SWITCH")
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "risk_limits.yaml"
    path.write_text(yaml.safe_dump(raw))
    return V2RiskEngine(ledger=store, config_path=path)


def _kill9(tmp_path: Path, point: str) -> Path:
    db = tmp_path / f"{point}.sqlite"
    marker = tmp_path / f"{point}.marker"
    proc = subprocess.Popen(
        [sys.executable, "-m", "runtime.fault_worker", "--db", str(db), "--marker", str(marker), "--crash-at", point],
        cwd=str(REPO),
    )
    for _ in range(200):
        if marker.is_file():
            break
        time.sleep(0.05)
        if proc.poll() is not None:
            raise RuntimeError(f"worker exited early rc={proc.returncode}")
    assert marker.is_file()
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait(timeout=5)
    return db


def test_reg_02b_kill_9_between_fill_and_stop(tmp_path: Path) -> None:
    db = _kill9(tmp_path, "after_fill_before_stop")
    store = SqliteLedgerStore(db, rates=RATES)
    clock = SimClock(NOW)
    broker = ClockedPaperBroker(clock=clock)
    result = recover(store, broker=broker, clock=clock, state_dir=tmp_path)
    assert result.status == "READY"
    for pos in store.open_positions():
        key = str(pos.get("instrument_id") or pos.get("symbol"))
        assert store.has_protective(key)
    store.close()


def test_reg_04a_kill_9_at_each_fault_matrix_point(tmp_path: Path) -> None:
    for point in FAULT_MATRIX_KILL_POINTS:
        db = _kill9(tmp_path / point, point)
        store = SqliteLedgerStore(db, rates=RATES)
        before = {r["instrument_id"]: r["net_qty"] for r in store.positions_v2()}
        assert before, f"missing seed at {point}"
        result = recover(store, broker=ClockedPaperBroker(clock=SimClock(NOW)), clock=SimClock(NOW), state_dir=tmp_path / point)
        after = {r["instrument_id"]: r["net_qty"] for r in store.positions_v2()}
        for inst, qty in before.items():
            assert after.get(inst) == qty
        assert result.status == "READY"
        store.close()


def test_reg_04b_broker_only_and_ledger_only_recon_mismatch(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
    clock = SimClock(NOW)
    broker = ClockedPaperBroker(clock=clock)
    broker._positions["BROKERONLY"] = Position("NIFTY 25000 PE", 65, 50.0, "BROKERONLY")
    mismatches = reconcile(broker, store, NOW)
    assert any(m.kind == "ORPHAN_BROKER" for m in mismatches)
    risk = _risk(tmp_path, store)
    intent = TradeIntent(symbol="NIFTY 24400 CE", side="BUY", lots=1, lot_size=65, decision_price=100.0, stop_loss=90.0)
    assert risk.check_entry(intent, now=NOW).reason_code == "RECON_MISMATCH"
    assert risk.check_exit(
        TradeIntent(symbol="NIFTY 24400 CE", side="SELL", lots=1, lot_size=65, purpose="EXIT", exit_reason="STOP_HIT"),
        now=NOW,
    ).approved

    store2 = SqliteLedgerStore(tmp_path / "led.sqlite", migrate_schema=True, rates=RATES)
    store2.insert_order(
        {
            "client_order_id": "aadled000000000000000000001",
            "symbol": "NIFTY 24400 CE",
            "instrument_id": INST,
            "side": "BUY",
            "qty": 65,
            "purpose": "ENTRY",
            "state": "SUBMITTED",
        }
    )
    store2.record_fill("aadled000000000000000000001", 65, 100.0, ts=NOW, side="BUY", symbol="NIFTY 24400 CE", instrument_id=INST)
    empty = ClockedPaperBroker(clock=clock)
    mm2 = reconcile(empty, store2, NOW)
    assert any(m.kind == "ORPHAN_INTERNAL" for m in mm2)
    risk2 = _risk(tmp_path / "b", store2)
    assert risk2.check_entry(intent, now=NOW).reason_code == "RECON_MISMATCH"
    assert risk2.check_exit(
        TradeIntent(symbol="NIFTY 24400 CE", side="SELL", lots=1, lot_size=65, purpose="EXIT", exit_reason="STOP_HIT"),
        now=NOW,
    ).approved
    store.close()
    store2.close()


def test_reg_05e_unreadable_halt_blocks_entries(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
    store.record_halt("2026-09-28", "founder", NOW.isoformat(), "MTM", "{not-json")
    result = recover(store, broker=ClockedPaperBroker(clock=SimClock(NOW)), clock=SimClock(NOW), state_dir=tmp_path)
    assert result.halt_unreadable is True
    risk = _risk(tmp_path, store)
    d = risk.check_entry(
        TradeIntent(symbol="NIFTY 24400 CE", side="BUY", lots=1, lot_size=65, decision_price=100.0, stop_loss=90.0),
        now=NOW,
    )
    assert d.reason_code == "HALT_UNREADABLE" and not d.approved
    assert risk.check_exit(
        TradeIntent(symbol="NIFTY 24400 CE", side="SELL", lots=1, lot_size=65, purpose="EXIT", exit_reason="STOP_HIT"),
        now=NOW,
    ).approved
    store.close()


def test_reg_05e_forced_closes_rebook_at_saved_time_and_price(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
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
    recover(store, broker=ClockedPaperBroker(clock=SimClock(NOW)), clock=SimClock(NOW), state_dir=tmp_path)
    fills = list(store.conn.execute("SELECT price, ts FROM fills WHERE client_order_id=?", ("aadhalt0000000000000000001",)))
    assert fills and float(fills[0][0]) == 88.5
    store.close()


def test_reg_05e_halt_unreadable_state(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
    store.record_halt("2026-09-28", "founder", NOW.isoformat(), "MTM", "{broken")
    snap = store.risk_snapshot(NOW, 60)
    assert snap["halt_unreadable"] is True
    assert RiskState(**{k: snap[k] for k in RiskState.__dataclass_fields__ if k in snap}).halt_unreadable
    store.close()
