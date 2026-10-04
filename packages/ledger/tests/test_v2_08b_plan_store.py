"""V2-08b plan-store fix-round. One test per verifier defect."""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from contracts.payloads import Decision
from oms.planner import CardPolicy, Side
from oms.router import Account

from ledger.migrate import CODE_SCHEMA_VERSION, list_migration_files, migrate
from ledger.v2 import SqliteLedgerStore

REPO = Path(__file__).resolve().parents[3]
NOW = datetime.fromisoformat("2026-09-28T10:00:00+05:30")
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"


def _schema_dump(path: Path) -> list[tuple[str, str, str | None]]:
    conn = sqlite3.connect(str(path))
    try:
        return [
            (str(r[0]), str(r[1]), r[2])
            for r in conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY 1, 2")
        ]
    finally:
        conn.close()


def _core_files() -> list[Path]:
    return [f for f in list_migration_files() if f.name.startswith(("001_", "002_"))]


def test_open_does_not_write_schema(tmp_path: Path) -> None:
    db = tmp_path / "aad.sqlite"
    migrate(db)
    before = _schema_dump(db)
    store = SqliteLedgerStore(db)
    assert store.schema_version == CODE_SCHEMA_VERSION
    store.close()
    assert _schema_dump(db) == before
    src = (REPO / "packages" / "ledger" / "src" / "ledger" / "v2.py").read_text(encoding="utf-8")
    assert "_ensure_entry_plan_payload" not in src
    assert "_install_charges_pending_trigger" not in src
    assert "ALTER TABLE entry_plans" not in src


def test_open_read_only_chmod_and_uri(tmp_path: Path) -> None:
    db = tmp_path / "aad.sqlite"
    store = SqliteLedgerStore(db, migrate_schema=True)
    store.upsert_plan(
        {
            "plan_id": "plan-ro",
            "account_id": "founder",
            "decision_id": "dec-ro",
            "signal_id": "sig-ro",
            "mode": "chase",
            "action": "CHASE",
            "status": "PENDING",
        }
    )
    store.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    store.close()
    os.chmod(db, 0o444)
    chmod_store = SqliteLedgerStore(db)
    got = chmod_store.get_plan("plan-ro")
    assert got is not None and got["status"] == "PENDING"
    chmod_store.close()
    uri = f"file:{db.resolve().as_posix()}?mode=ro"
    uri_store = SqliteLedgerStore(uri)
    again = uri_store.get_plan("plan-ro")
    assert again is not None and again["decision_id"] == "dec-ro"
    uri_store.close()


def test_concurrent_open_and_migrate_are_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "aad.sqlite"
    migrate(db, files=_core_files())
    errors: list[BaseException] = []

    def apply_migrate() -> None:
        try:
            migrate(db)
        except (OSError, sqlite3.Error, RuntimeError) as exc:
            errors.append(exc)

    starters = [threading.Thread(target=apply_migrate) for _ in range(4)]
    for thread in starters:
        thread.start()
    for thread in starters:
        thread.join()
    assert errors == []

    def open_store() -> None:
        try:
            store = SqliteLedgerStore(db)
            store.get_plan("missing")
            store.close()
        except (OSError, sqlite3.Error, RuntimeError) as exc:
            errors.append(exc)

    openers = [threading.Thread(target=open_store) for _ in range(8)]
    for thread in openers:
        thread.start()
    for thread in openers:
        thread.join()
    assert errors == []
    store = SqliteLedgerStore(db)
    assert store._has_column("entry_plans", "payload_json")
    store.close()
    migrate(db)
    again = SqliteLedgerStore(db)
    assert again._has_column("entry_plans", "payload_json")
    again.close()


def test_entry_plan_payload_exact_type_round_trip(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True)
    created = NOW
    bar_close = NOW - timedelta(seconds=1)
    expires = NOW + timedelta(seconds=2)
    policy = CardPolicy(mode="chase", max_chase_ticks=2, chase_timeout_s=2.0)
    decision = Decision(
        decision_id="dec-1",
        underlying="NIFTY",
        decision="ENTER",
        signal_ids=["sig-1"],
        instrument_id=INST,
        lots=2,
        lot_size=65,
    )
    row = store.upsert_plan(
        {
            "plan_id": "plan-types",
            "account_id": "founder",
            "decision_id": "dec-1",
            "signal_id": "sig-1",
            "mode": "chase",
            "action": "CHASE",
            "status": "PENDING",
            "created_at": created,
            "bar_close_ts": bar_close,
            "expires_at": expires,
            "policy": policy,
            "decision": decision,
            "account": Account("founder"),
            "side": Side.BUY,
            "limit_price": Decimal("151.35"),
            "zone_price": Decimal("144.10"),
            "entry_distance_atr": Decimal("1.2345"),
            "signal_candle_atr": Decimal("2.5"),
        }
    )
    store.close()
    again = SqliteLedgerStore(tmp_path / "aad.sqlite")
    got = again.get_plan("plan-types")
    assert got is not None
    assert isinstance(got["limit_price"], Decimal) and got["limit_price"] == Decimal("151.35")
    assert isinstance(got["zone_price"], Decimal) and got["zone_price"] == Decimal("144.10")
    assert got["entry_distance_atr"] == Decimal("1.2345")
    assert not isinstance(got["entry_distance_atr"], float)
    assert isinstance(got["created_at"], datetime) and got["created_at"].tzinfo is not None
    assert got["created_at"] == created
    assert isinstance(got["bar_close_ts"], datetime) and got["bar_close_ts"].tzinfo is not None
    assert got["bar_close_ts"] == bar_close
    assert isinstance(got["expires_at"], datetime) and got["expires_at"].tzinfo is not None
    assert got["expires_at"] == expires
    assert isinstance(got["policy"], CardPolicy)
    assert got["policy"].chase_timeout_s == 2.0
    assert isinstance(got["side"], Side) and got["side"] is Side.BUY
    assert isinstance(got["decision"], Decision)
    assert isinstance(got["account"], Account)
    assert row["entry_distance_atr"] == Decimal("1.2345")
    again.close()


def test_upsert_plan_preserves_immutable_fields(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True)
    created = NOW
    store.upsert_plan(
        {
            "plan_id": "plan-imm",
            "account_id": "founder",
            "decision_id": "dec-orig",
            "signal_id": "sig-orig",
            "mode": "chase",
            "action": "CHASE",
            "status": "PENDING",
            "created_at": created,
            "limit_price": Decimal("151.35"),
        }
    )
    store.upsert_plan(
        {
            "plan_id": "plan-imm",
            "decision_id": "dec-hacked",
            "signal_id": "sig-hacked",
            "mode": "pullback_limit",
            "action": "LIMIT",
            "created_at": created + timedelta(hours=1),
            "status": "WORKING",
            "client_order_id": "aad1",
            "limit_price": Decimal("144.10"),
        }
    )
    got = store.get_plan("plan-imm")
    assert got is not None
    assert got["decision_id"] == "dec-orig"
    assert got["signal_id"] == "sig-orig"
    assert got["mode"] == "chase"
    assert got["action"] == "CHASE"
    assert got["created_at"] == created
    assert got["status"] == "WORKING"
    assert got["client_order_id"] == "aad1"
    assert got["limit_price"] == Decimal("144.10")
    store.close()
