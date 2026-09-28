"""Charges match ledger.charges on a known ticket."""

from __future__ import annotations

from datetime import datetime

from ledger.charges import load_rates, order_charges

from exitlab.clock import IST
from exitlab.costs import fill_charges, load_cost_rates, round_trip_charges
from exitlab.types import Fill


def test_round_trip_matches_ledger() -> None:
    rates = load_cost_rates()
    direct = load_rates(by_exchange=True)
    buy = order_charges("BUY", 65, 180.0, direct, exchange="NSE")
    sell = order_charges("SELL", 65, 190.0, direct, exchange="NSE")
    got = round_trip_charges(65, 180.0, 190.0, rates, exchange="NSE")
    assert abs(got - float(buy["total"] + sell["total"])) < 1e-9
    assert got > 0


def test_fill_charges_has_stt_on_sell_only() -> None:
    rates = load_cost_rates()
    ts = datetime(2026, 9, 17, 10, 0, tzinfo=IST)
    buy = fill_charges(Fill("BUY", ts, 65, 100.0, "test", "ENTRY"), rates)
    sell = fill_charges(Fill("SELL", ts, 65, 100.0, "test", "EXIT"), rates)
    assert buy["stt"] == 0.0
    assert sell["stt"] > 0
    assert buy["stamp"] > 0
    assert sell["stamp"] == 0.0
