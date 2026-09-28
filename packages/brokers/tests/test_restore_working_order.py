"""ClockedPaperBroker.restore_working_order: price + meta so later quotes can fill."""

from __future__ import annotations

from datetime import datetime, timedelta

from brokers.fills import ClockedPaperBroker, Quote
from contracts.clock import IST, SimClock

NOW = datetime(2026, 9, 28, 10, 1, tzinfo=IST)
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"


def test_restore_working_order_depth_fills_without_place() -> None:
    clock = SimClock(NOW)
    broker = ClockedPaperBroker(clock=clock)
    placed = 0
    orig = broker.place_order

    def _count(*a, **k):  # type: ignore[no-untyped-def]
        nonlocal placed
        placed += 1
        return orig(*a, **k)

    broker.place_order = _count  # type: ignore[method-assign]
    row = {
        "client_order_id": "aad-entry-1",
        "instrument_id": INST,
        "symbol": "NIFTY 24400 CE",
        "side": "BUY",
        "qty": 130,
        "lots": 2,
        "lot_size": 65,
        "order_type": "LIMIT",
        "price": 151.30,
        "purpose": "ENTRY",
        "status": "SUBMITTED",
    }
    plan = {
        "sent_at": NOW,
        "limit_price": 151.30,
        "lots": 2,
        "lot_size": 65,
        "instrument_id": INST,
        "decision": type("D", (), {"shadow": {"chosen": "ITM100"}})(),
    }
    order = broker.restore_working_order(row, plan=plan, now=clock.now())
    assert placed == 0
    assert order.client_order_id == "aad-entry-1"
    assert order.price == 151.30
    assert order.intent.price == 151.30
    assert broker._order_meta["aad-entry-1"].price == 151.30
    clock.advance_by(timedelta(milliseconds=250))
    broker.on_depth(Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST))
    assert order.state.value == "FILLED"
    assert placed == 0
