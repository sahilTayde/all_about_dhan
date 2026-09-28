"""V2-10 fix-round tests. Each name is one verifier failure from PR #58."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from ledger.charges import load_rates, order_charges
from ledger.v2 import SqliteLedgerStore, money

REPO = Path(__file__).resolve().parents[3]
RATES = load_rates(REPO / "config" / "charges.yaml", by_exchange=True)
NOW = datetime.fromisoformat("2026-09-28T10:00:00+05:30")
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
SYM = "NIFTY 24400 CE"


def _store(tmp_path: Path, *, rates: dict[str, Any] | None = RATES) -> SqliteLedgerStore:
    return SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=rates)


def _order(
    store: SqliteLedgerStore,
    cid: str,
    *,
    qty: int = 65,
    lots: int | None = None,
    lot_size: int | None = None,
    side: str = "BUY",
    symbol: str = SYM,
    instrument_id: str = INST,
) -> None:
    row: dict[str, Any] = {
        "client_order_id": cid,
        "symbol": symbol,
        "instrument_id": instrument_id,
        "side": side,
        "qty": qty,
        "purpose": "ENTRY" if side == "BUY" else "EXIT",
        "state": "SUBMITTED",
        "account_id": "founder",
    }
    if lots is not None:
        row["lots"] = lots
    if lot_size is not None:
        row["lot_size"] = lot_size
    store.insert_order(row)


def test_atomic_fill_write_rollback_and_replay(tmp_path: Path) -> None:
    db = tmp_path / "aad.sqlite"
    store = SqliteLedgerStore(db, migrate_schema=True, rates=RATES)
    _order(store, "aadatom0000000000000000001")
    store._crash_after = "fills"
    with pytest.raises(RuntimeError, match="injected crash after fills"):
        store.record_fill("aadatom0000000000000000001", 65, 100, ts=NOW, side="BUY", symbol=SYM, instrument_id=INST)
    store.close()

    reopened = SqliteLedgerStore(db, rates=RATES)
    fills = reopened.conn.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
    pos = reopened.conn.execute("SELECT COALESCE(SUM(net_qty),0) FROM positions_v2").fetchone()[0]
    charges = reopened.conn.execute("SELECT COUNT(*) FROM charges").fetchone()[0]
    assert fills == 0 and charges == 0 and int(pos) == 0
    reopened.record_fill("aadatom0000000000000000001", 65, 100, ts=NOW, side="BUY", symbol=SYM, instrument_id=INST)
    fills = reopened.conn.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
    qty = reopened.conn.execute("SELECT net_qty FROM positions_v2").fetchone()[0]
    assert fills == 1 and int(qty) == 65
    reopened.close()


def test_record_fill_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _order(store, "aadidem0000000000000000001")
    a = store.record_fill("aadidem0000000000000000001", 65, 100, ts=NOW, side="BUY", symbol=SYM, instrument_id=INST)
    b = store.record_fill("aadidem0000000000000000001", 65, 100, ts=NOW, side="BUY", symbol=SYM, instrument_id=INST)
    assert b.get("idempotent") is True
    assert a["fill_id"] == b["fill_id"]
    fills = store.conn.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
    charges = store.conn.execute("SELECT COUNT(*) FROM charges").fetchone()[0]
    qty = store.conn.execute("SELECT net_qty FROM positions_v2").fetchone()[0]
    filled = store.conn.execute(
        "SELECT filled_qty FROM orders WHERE client_order_id=?", ("aadidem0000000000000000001",)
    ).fetchone()[0]
    assert fills == 1 and charges == 1 and int(qty) == 65 and int(filled) == 65
    store.close()


def test_rebook_forced_closes_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    close = {
        "client_order_id": "aadhalt0000000000000000001",
        "instrument_id": INST,
        "symbol": SYM,
        "qty": 65,
        "price": "88.50",
        "ts": NOW.isoformat(),
        "side": "SELL",
        "account_id": "founder",
    }
    store.insert_order(
        {
            "client_order_id": "aadhalt0000000000000000001",
            "symbol": SYM,
            "instrument_id": INST,
            "side": "SELL",
            "qty": 65,
            "purpose": "EXIT",
            "state": "SUBMITTED",
        }
    )
    store.book_forced_close(close)
    store.book_forced_close(close)
    fills = store.conn.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
    qty = store.conn.execute("SELECT net_qty FROM positions_v2").fetchone()[0]
    assert fills == 1 and int(qty) == -65
    store.close()


def test_recharge_pending_finalizes_once(tmp_path: Path) -> None:
    store = _store(tmp_path, rates=None)
    _order(store, "aadpend0000000000000000001")
    store.record_fill("aadpend0000000000000000001", 65, 100, ts=NOW, side="BUY", symbol=SYM, instrument_id=INST)
    n1 = store.recharge_pending(RATES)
    n2 = store.recharge_pending(RATES)
    finals = list(store.conn.execute("SELECT total, charges_status FROM charges"))
    assert n1 == 1 and n2 == 0
    assert len(finals) == 1 and finals[0][1] == "FINAL"
    want = money(order_charges("BUY", 65, 100, RATES, exchange="NSE")["total"])
    got = money(finals[0][0])
    assert got == want
    trade = store.conn.execute("SELECT charges FROM trades").fetchone()
    assert money(trade[0]) == want
    store.close()


def test_realized_pnl_close_and_rebuild(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _order(store, "aadbuy00000000000000000001", side="BUY")
    store.record_fill("aadbuy00000000000000000001", 65, 100, ts=NOW, side="BUY", symbol=SYM, instrument_id=INST)
    _order(store, "aadsell0000000000000000001", side="SELL")
    store.record_fill("aadsell0000000000000000001", 65, 110, ts=NOW, side="SELL", symbol=SYM, instrument_id=INST)
    trades = list(store.conn.execute("SELECT * FROM trades"))
    closed = [t for t in trades if t["status"] == "CLOSED"]
    assert len(trades) == 1 and len(closed) == 1
    assert money(closed[0]["gross_pnl"]) == money(650)
    pos = store.conn.execute("SELECT net_qty FROM positions_v2").fetchone()
    assert int(pos[0]) == 0
    fill_charges = store.conn.execute(
        "SELECT COALESCE(SUM(total),0) FROM charges WHERE charges_status='FINAL' AND total > 0"
    ).fetchone()[0]
    assert money(closed[0]["charges"]) == money(fill_charges)
    assert money(closed[0]["net_pnl"]) == money(650) - money(fill_charges)
    rebuilt_gross = money(0)
    fills = list(store.conn.execute("SELECT side, qty, price FROM fills ORDER BY id"))
    assert len(fills) == 2
    buy_px, sell_px = money(fills[0]["price"]), money(fills[1]["price"])
    rebuilt_gross = (sell_px - buy_px) * money(fills[0]["qty"])
    assert rebuilt_gross == money(650)
    assert money(closed[0]["gross_pnl"]) == rebuilt_gross
    store.close()


def test_insert_order_qty_not_multiplied(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _order(store, "aadqty00000000000000000001", qty=65, lots=1, lot_size=65)
    qty = store.conn.execute(
        "SELECT qty FROM orders WHERE client_order_id=?", ("aadqty00000000000000000001",)
    ).fetchone()[0]
    assert int(qty) == 65
    store.close()


def test_qty_rejects_non_multiple_of_lot_size(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="whole multiple"):
        store.insert_order(
            {
                "client_order_id": "aadbadqty0000000000000001",
                "symbol": SYM,
                "instrument_id": INST,
                "side": "BUY",
                "qty": 64,
                "lot_size": 65,
                "purpose": "ENTRY",
                "state": "SUBMITTED",
            }
        )
    _order(store, "aadokqty000000000000000001")
    with pytest.raises(ValueError, match="whole multiple"):
        store.record_fill("aadokqty000000000000000001", 64, 100, ts=NOW, side="BUY", symbol=SYM, instrument_id=INST)
    store.close()


def test_money_math_decimal_not_float() -> None:
    src = (REPO / "packages" / "ledger" / "src" / "ledger" / "v2.py").read_text(encoding="utf-8")
    assert "from decimal import" in src
    assert "Decimal" in src
    assert "float(qty)*float(price)" not in src
    assert "float(qty) * float(price)" not in src
    assert "money(" in src and "money_sql(" in src
    assert money("100.10") == Decimal("100.10")
    assert money(Decimal("0.1") + Decimal("0.2")) == Decimal("0.30")


def test_record_fill_uses_explicit_txn_not_autocommit(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.conn.isolation_level is None
    src = (REPO / "packages" / "ledger" / "src" / "ledger" / "v2.py").read_text(encoding="utf-8")
    assert "BEGIN IMMEDIATE" in src
    _order(store, "aadtxn00000000000000000001")
    store._crash_after = "fills"
    with pytest.raises(RuntimeError, match="injected crash after fills"):
        store.record_fill("aadtxn00000000000000000001", 65, 100, ts=NOW, side="BUY", symbol=SYM, instrument_id=INST)
    assert store.conn.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 0
    store.close()


def test_entry_plans_round_trip_on_sqlite_store(tmp_path: Path) -> None:
    store = _store(tmp_path)
    row = store.upsert_plan(
        {
            "plan_id": "plan-1",
            "account_id": "founder",
            "decision_id": "dec-1",
            "signal_id": "sig-1",
            "mode": "chase",
            "action": "CHASE",
            "status": "PENDING",
            "limit_price": 151.35,
            "instrument_id": INST,
        }
    )
    assert row["plan_id"] == "plan-1"
    assert store.get_plan("plan-1")["status"] == "PENDING"
    assert len(store.pending_plans()) == 1
    store.upsert_plan({**row, "status": "WORKING", "client_order_id": "aad1"})
    assert store.pending_plans()[0]["client_order_id"] == "aad1"
    assert store.entry_plans["plan-1"]["instrument_id"] == INST
    store.close()
