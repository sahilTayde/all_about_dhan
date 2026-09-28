"""REG-06b, REG-16c, REG-17a-d (V2-10 ledger)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from ledger import Ledger, SqliteLedgerStore, load_rates, migrate
from ledger.charges import exchange_for, order_charges

REPO = Path(__file__).resolve().parents[2]
RATES = load_rates(REPO / "config" / "charges.yaml", by_exchange=True)
NOW = datetime.fromisoformat("2026-09-28T10:00:00+05:30")


def test_reg_06b_first_bad_line_written_once_survives_restart(tmp_path: Path) -> None:
    db = tmp_path / "aad.sqlite"
    store = SqliteLedgerStore(db, migrate_schema=True)
    store.record_ingest_error("tape", "/tmp/day.jsonl", 3, 120, "not json", "{bad")
    store.record_ingest_error("tape", "/tmp/day.jsonl", 3, 999, "dup", "{bad")
    assert len(store.ingest_errors()) == 1
    store.close()
    again = SqliteLedgerStore(db)
    rows = again.ingest_errors()
    assert (
        len(rows) == 1
        and rows[0]["byte_offset"] == 120
        and len(rows[0]["line_sha256"]) == 64
    )
    again.close()


def test_reg_16c_pending_charges_never_zero_then_recharged(tmp_path: Path) -> None:
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
    assert row["components"].get("total", None) != 0.0
    pending = store.conn.execute(
        "SELECT total FROM charges WHERE charges_status='PENDING'"
    ).fetchone()
    assert pending is not None and pending[0] != 0
    assert store.recharge_pending(RATES) == 1
    final = store.conn.execute(
        "SELECT total FROM charges WHERE charges_status='FINAL'"
    ).fetchone()
    assert final is not None and final[0] > 0
    store.close()


def test_reg_17a_every_trade_has_exchange_from_underlying(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
    cases = (
        (
            "aadnse00000000000000000001",
            "NIFTY 24400 CE",
            "NSE_FNO:NIFTY:2026-09-29:24400:CE",
            65,
        ),
        (
            "aadbse00000000000000000001",
            "SENSEX 82000 CE",
            "BSE_FNO:SENSEX:2026-09-29:82000:CE",
            20,
        ),
    )
    for cid, symbol, inst, qty in cases:
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
        row = store.record_fill(
            cid, qty, 100.0, ts=NOW, side="BUY", symbol=symbol, instrument_id=inst
        )
        ex = store.conn.execute(
            "SELECT exchange FROM trades WHERE trade_id=?", (row["trade_id"],)
        ).fetchone()[0]
        assert ex == exchange_for(symbol, RATES)
        assert ex in ("NSE", "BSE")
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
    got = store.conn.execute(
        "SELECT total FROM charges WHERE client_order_id=? AND charges_status='FINAL'",
        ("aadbse00000000000000000002",),
    ).fetchone()[0]
    assert row["exchange"] == "BSE" and got == pytest.approx(want["total"])
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
    assert (
        store.conn.execute(
            "SELECT exchange FROM trades WHERE trade_id=?", (tid,)
        ).fetchone()[0]
        == "NSE"
    )
    store.close()
