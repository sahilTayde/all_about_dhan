"""Subprocess worker for REG-02b / REG-04a. Writes a marker, then sleeps until SIGKILL."""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

from contracts.clock import IST
from ledger.charges import load_rates
from ledger.v2 import SqliteLedgerStore

NOW = datetime(2026, 9, 28, 10, 5, tzinfo=IST)
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"


def _seed_position(store: SqliteLedgerStore) -> None:
    store.insert_order(
        {
            "client_order_id": "seedentry00000000000000001",
            "symbol": "NIFTY 24400 CE",
            "instrument_id": INST,
            "side": "BUY",
            "qty": 65,
            "lots": 1,
            "lot_size": 65,
            "purpose": "ENTRY",
            "state": "SUBMITTED",
            "account_id": "founder",
            "signal_id": "sg_seed",
        }
    )
    store.record_fill(
        "seedentry00000000000000001",
        65,
        100.0,
        ts=NOW,
        side="BUY",
        symbol="NIFTY 24400 CE",
        instrument_id=INST,
        fill_model="fcmeas",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--marker", required=True)
    p.add_argument("--crash-at", required=True)
    args = p.parse_args(argv)
    db = Path(args.db)
    rates = load_rates(by_exchange=True)
    store = SqliteLedgerStore(db, migrate_schema=True, rates=rates)
    _seed_position(store)
    cid = "aadcrash000000000000000001"
    if args.crash_at == "after_new_before_submit":
        store.insert_order(
            {
                "client_order_id": cid,
                "symbol": "NIFTY 24400 CE",
                "instrument_id": INST,
                "side": "BUY",
                "qty": 65,
                "purpose": "ENTRY",
                "state": "NEW",
                "account_id": "founder",
            }
        )
    elif args.crash_at == "after_broker_fill_before_ledger":
        store.insert_order(
            {
                "client_order_id": cid,
                "symbol": "NIFTY 24400 CE",
                "instrument_id": INST,
                "side": "BUY",
                "qty": 65,
                "purpose": "ENTRY",
                "state": "SUBMITTED",
                "account_id": "founder",
            }
        )
        # fill exists only in this process; not written to the ledger
    elif args.crash_at == "after_fill_before_stop":
        store.insert_order(
            {
                "client_order_id": cid,
                "symbol": "NIFTY 24400 CE",
                "instrument_id": INST + ":2",
                "side": "BUY",
                "qty": 65,
                "purpose": "ENTRY",
                "state": "SUBMITTED",
                "account_id": "founder",
                "signal_id": "sg_crash",
            }
        )
        store.record_fill(
            cid,
            65,
            110.0,
            ts=NOW,
            side="BUY",
            symbol="NIFTY 24400 CE",
            instrument_id=INST + ":2",
            fill_model="fcmeas",
        )
    else:
        raise SystemExit(f"unknown crash point {args.crash_at}")
    store.conn.execute("PRAGMA wal_checkpoint(FULL)")
    store.conn.commit()
    store.close()
    Path(args.marker).write_text(args.crash_at, encoding="utf-8")
    time.sleep(3600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
