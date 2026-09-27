"""Fill models never use a price from after the order's decision/engine time."""

from __future__ import annotations

from datetime import datetime, timedelta

from brokers.fills import FillOrder, Quote, choose_fill
from contracts.clock import SimClock
from helpers import INST, NOW
from risk_engine import IST


def test_fill_model_never_uses_price_after_decision_time() -> None:
    """Planted future quote after decision_ts / clock.now() is invisible (no look-ahead)."""
    clock = SimClock(NOW)
    order = FillOrder(
        client_order_id="aad" + "0" * 24,
        side="BUY",
        order_type="MARKET",
        available_ts=NOW,
        decision_ts=NOW,
        lots=2,
        lot_size=65,
        instrument_id=INST,
        moneyness="ITM100",
        latency_ms=200,
    )
    clock.advance_by(timedelta(milliseconds=200))
    now = clock.now()
    good = Quote(available_ts=now, bid=151.10, ask=151.35, ltp=151.20, instrument_id=INST)
    future = Quote(
        available_ts=NOW + timedelta(seconds=30),
        bid=140.00,
        ask=140.05,
        ltp=140.00,
        instrument_id=INST,
    )
    # Future print sits after decision_ts and after engine now — must not be used.
    assert future.available_ts > order.decision_ts
    assert future.available_ts > now
    got = choose_fill(order, [good, future], ltp=151.20, now=now)
    assert got is not None
    px, model = got
    assert model == "depth"
    assert px != 140.05
    assert abs(px - 151.35) < 1e-9 or abs(px - 151.40) < 1e-9  # ask ± tiny impact

    leaked = choose_fill(order, [good, future], ltp=140.00, now=clock.now())
    assert leaked is not None
    assert leaked[0] != 140.05
    _ = datetime, IST
