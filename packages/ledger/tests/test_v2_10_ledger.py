"""V2-10 ledger acceptance: migrations, schema refuse, PENDING, exchange, ingest, legacy."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from ledger import Ledger, SchemaTooNew, SqliteLedgerStore, load_rates, migrate
from ledger.charges import exchange_for
from ledger.migrate import CODE_SCHEMA_VERSION, LegacyPathError, is_legacy_path
from ledger.store import DEFAULT_LEDGER_PATH

REPO = Path(__file__).resolve().parents[3]
RATES = load_rates(REPO / "config" / "charges.yaml", by_exchange=True)
NOW = datetime.fromisoformat("2026-09-28T10:00:00+05:30")


def test_legacy_path_not_migrated_unless_explicit(tmp_path: Path) -> None:
    legacy = tmp_path / "data" / "ledger" / "ledger.sqlite"
    legacy.parent.mkdir(parents=True)
    assert is_legacy_path(legacy)
    with pytest.raises(LegacyPathError):
        migrate(legacy)
    with pytest.raises(LegacyPathError):
        SqliteLedgerStore(legacy)
    ver = migrate(legacy, allow_legacy=True)
    assert ver == CODE_SCHEMA_VERSION


def test_legacy_ledger_does_not_create_v2_tables() -> None:
    led = Ledger(":memory:", rates=load_rates(REPO / "config" / "charges.yaml"))
    names = {r[0] for r in led.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "positions_v2" not in names
    assert "schema_version" not in names
    led.close()


def test_engine_refuses_newer_schema(tmp_path: Path) -> None:
    db = tmp_path / "aad.sqlite"
    migrate(db)
    conn = __import__("sqlite3").connect(str(db))
    conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (99, '2099-01-01T00:00:00+05:30')")
    conn.commit()
    conn.close()
    with pytest.raises(SchemaTooNew):
        SqliteLedgerStore(db)


def test_reg_16c_pending_charges_never_zero(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=None)
    store.insert_order(
        {
            "client_order_id": "aadpending0000000000000001",
            "symbol": "NIFTY 24400 CE",
            "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24400:CE",
            "side": "BUY",
            "qty": 65,
            "purpose": "ENTRY",
            "state": "SUBMITTED",
        }
    )
    row = store.record_fill(
        "aadpending0000000000000001",
        65,
        100.0,
        ts=NOW,
        side="BUY",
        symbol="NIFTY 24400 CE",
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
    )
    assert row["charges_status"] == "PENDING"
    assert row["components"] == {}
    assert row["components"].get("total", None) != 0.0
    pending = store.conn.execute("SELECT total, charges_status FROM charges WHERE charges_status='PENDING'").fetchone()
    assert pending is not None and pending[1] == "PENDING" and pending[0] != 0
    trade = store.conn.execute("SELECT charges FROM trades WHERE trade_id=?", (row["trade_id"],)).fetchone()
    assert trade[0] == 0  # not booked as a free fill
    n = store.recharge_pending(RATES)
    assert n == 1
    final = store.conn.execute("SELECT total, charges_status FROM charges WHERE charges_status='FINAL'").fetchone()
    assert final is not None and final[0] > 0
    store.close()


def test_reg_17a_trade_exchange_from_underlying(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
    for cid, symbol, inst, qty in (
        ("aadnse00000000000000000001", "NIFTY 24400 CE", "NSE_FNO:NIFTY:2026-09-29:24400:CE", 65),
        ("aadbse00000000000000000001", "SENSEX 82000 CE", "BSE_FNO:SENSEX:2026-09-29:82000:CE", 20),
    ):
        store.insert_order(
            {
                "client_order_id": cid,
                "symbol": symbol,
                "instrument_id": inst,
                "side": "BUY",
                "qty": qty,
                "purpose": "ENTRY",
                "state": "SUBMITTED",
            }
        )
        row = store.record_fill(cid, qty, 100.0, ts=NOW, side="BUY", symbol=symbol, instrument_id=inst)
        trade = store.conn.execute("SELECT exchange FROM trades WHERE trade_id=?", (row["trade_id"],)).fetchone()
        assert trade[0] == exchange_for(symbol, RATES)
    store.close()


def test_reg_17b_unmapped_underlying_refused(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
    store.insert_order(
        {
            "client_order_id": "aadbad00000000000000000001",
            "symbol": "FOO 100 CE",
            "instrument_id": "NSE_FNO:FOO:2026-09-29:100:CE",
            "side": "BUY",
            "qty": 65,
            "purpose": "ENTRY",
            "state": "SUBMITTED",
        }
    )
    with pytest.raises(ValueError, match="no exchange|unmapped"):
        store.record_fill(
            "aadbad00000000000000000001",
            65,
            100.0,
            ts=NOW,
            side="BUY",
            symbol="FOO 100 CE",
            instrument_id="NSE_FNO:FOO:2026-09-29:100:CE",
        )
    store.close()


def test_reg_17c_charges_match_tagged_exchange(tmp_path: Path) -> None:
    from ledger.charges import order_charges

    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
    store.insert_order(
        {
            "client_order_id": "aadbse00000000000000000002",
            "symbol": "SENSEX 82000 CE",
            "instrument_id": "BSE_FNO:SENSEX:2026-09-29:82000:CE",
            "side": "BUY",
            "qty": 20,
            "purpose": "ENTRY",
            "state": "SUBMITTED",
        }
    )
    row = store.record_fill(
        "aadbse00000000000000000002",
        20,
        100.0,
        ts=NOW,
        side="BUY",
        symbol="SENSEX 82000 CE",
        instrument_id="BSE_FNO:SENSEX:2026-09-29:82000:CE",
    )
    want = order_charges("BUY", 20, 100.0, RATES, exchange="BSE")
    ch = store.conn.execute(
        "SELECT exchange, total FROM charges WHERE client_order_id=? AND charges_status='FINAL'",
        ("aadbse00000000000000000002",),
    ).fetchone()
    assert row["exchange"] == "BSE"
    assert ch[1] == pytest.approx(want["total"])
    store.close()


def test_reg_17d_migration_backfills_old_rows(tmp_path: Path) -> None:
    db = tmp_path / "old.sqlite"
    led = Ledger(db, rates=load_rates(REPO / "config" / "charges.yaml"))
    led.record_order(
        {
            "client_order_id": "E1",
            "broker": "paper",
            "mode": "paper",
            "symbol": "NIFTY-CE",
            "instrument_id": "1",
            "side": "BUY",
            "qty": 65,
            "order_type": "MARKET",
            "purpose": "ENTRY",
            "filled_qty": 0,
        },
        "NEW",
        "SUBMITTED",
        "test",
        NOW,
    )
    tid = led.record_fill("E1", 65, 100.0, NOW)
    led.close()
    migrate(db)
    store = SqliteLedgerStore(db)
    row = store.conn.execute("SELECT exchange FROM trades WHERE trade_id=?", (tid,)).fetchone()
    assert row[0] == "NSE"
    store.close()


def test_reg_06b_first_bad_line_ingest_errors_survives_restart(tmp_path: Path) -> None:
    db = tmp_path / "aad.sqlite"
    store = SqliteLedgerStore(db, migrate_schema=True)
    store.record_ingest_error("tape", "/tmp/day.jsonl", 3, 120, "not json", "{bad")
    store.record_ingest_error("tape", "/tmp/day.jsonl", 3, 120, "not json again", "{bad")
    rows = store.ingest_errors()
    assert len(rows) == 1
    assert rows[0]["line_no"] == 3 and rows[0]["byte_offset"] == 120
    assert len(rows[0]["line_sha256"]) == 64
    store.close()
    again = SqliteLedgerStore(db)
    assert len(again.ingest_errors()) == 1
    again.close()


def test_checkpoint_outbox_same_transaction(tmp_path: Path) -> None:
    from contracts.envelope import Envelope

    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True)
    env = Envelope(
        v=2,
        event_type="CLOCK",
        event_id="evt_1",
        stream="md:clock",
        source="test",
        event_ts=NOW.isoformat(),
        available_ts=NOW.isoformat(),
        timestamp=NOW.isoformat(),
        account_id=None,
        correlation_id=None,
        causation_id=None,
        payload={"seq": 1},
    )
    with store.transaction():
        store.checkpoint(env)
    assert store.get_last_checkpoint() is not None
    drained = store.drain_outbox()
    assert len(drained) == 1 and drained[0]["event_id"] == "evt_1"
    assert store.drain_outbox() == []
    store.close()


def test_positions_v2_round_trip(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True)
    store.upsert_position_v2("founder", "NSE_FNO:NIFTY:2026-09-29:24400:CE", 65, 100.0, strategy_id="TEST")
    rows = store.positions_v2()
    assert rows[0]["net_qty"] == 65 and rows[0]["strategy_id"] == "TEST"
    inst = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
    got = store.get_position(inst)
    assert got is not None and int(got["net_qty"]) == 65
    store.close()


def test_insert_order_persists_price_for_rebuild(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True)
    store.insert_order(
        {
            "client_order_id": "aad-entry-1",
            "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24400:CE",
            "side": "BUY",
            "lots": 2,
            "lot_size": 65,
            "order_type": "LIMIT",
            "price": 151.30,
            "purpose": "ENTRY",
            "state": "SUBMITTED",
        }
    )
    row = store.get_order("aad-entry-1")
    assert row is not None
    assert float(row["price"]) == 151.30
    store.close()


def test_default_ledger_path_is_legacy() -> None:
    assert is_legacy_path(DEFAULT_LEDGER_PATH)


def test_legacy_frozen_script_still_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/ci/check_frozen_legacy.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
