"""V2-10 fix-round recovery tests named after each verifier failure."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from brokers.fills import ClockedPaperBroker  # type: ignore[import-untyped]
from brokers.paper import PaperBroker  # type: ignore[import-untyped]
from contracts.clock import IST, SimClock
from ledger.charges import load_rates
from ledger.v2 import SqliteLedgerStore

from runtime.recovery import rebuild_paper_broker, recover

REPO = Path(__file__).resolve().parents[3]
RATES = load_rates(REPO / "config" / "charges.yaml", by_exchange=True)
NOW = datetime(2026, 9, 28, 10, 5, tzinfo=IST)
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
SYM = "NIFTY 24400 CE"


def test_rebook_forced_closes_idempotent(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
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
    store.record_halt(
        "2026-09-28",
        "founder",
        NOW.isoformat(),
        "MTM",
        [
            {
                "client_order_id": "aadhalt0000000000000000001",
                "instrument_id": INST,
                "symbol": SYM,
                "qty": 65,
                "price": "88.50",
                "ts": NOW.isoformat(),
                "side": "SELL",
                "account_id": "founder",
            }
        ],
    )
    clock = SimClock(NOW)
    broker = ClockedPaperBroker(clock=clock)
    recover(store, broker=broker, clock=clock, state_dir=tmp_path / "r1")
    fills1 = store.conn.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
    qty1 = store.conn.execute("SELECT net_qty FROM positions_v2").fetchone()[0]
    recover(store, broker=ClockedPaperBroker(clock=clock), clock=clock, state_dir=tmp_path / "r2")
    fills2 = store.conn.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
    qty2 = store.conn.execute("SELECT net_qty FROM positions_v2").fetchone()[0]
    assert fills1 == 1 and fills2 == 1
    assert int(qty1) == -65 and int(qty2) == -65
    store.close()


def test_rebuild_nifty_lots_one_lot_size_65(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True, rates=RATES)
    store.insert_order(
        {
            "client_order_id": "aadopen0000000000000000001",
            "symbol": SYM,
            "instrument_id": INST,
            "side": "BUY",
            "qty": 65,
            "lots": 1,
            "lot_size": 65,
            "purpose": "ENTRY",
            "state": "SUBMITTED",
        }
    )
    clock = SimClock(NOW)
    broker = ClockedPaperBroker(clock=clock)
    rebuild_paper_broker(broker, store)
    order = broker.orders["aadopen0000000000000000001"]
    assert order.intent.lots == 1 and order.intent.lot_size == 65
    assert order.intent.qty == 65
    paper = PaperBroker()
    paper.rebuild_from_ledger(store)
    rebuilt = paper.orders["aadopen0000000000000000001"]
    assert rebuilt.intent.lots == 1 and rebuilt.intent.lot_size == 65
    assert rebuilt.intent.qty == 65
    store.close()
