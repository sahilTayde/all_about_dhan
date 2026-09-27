"""Property tests for ledger.charges.order_charges (spec §3, cost realism §6.5).

Each property names a mutant it catches:
- non-negativity / total = sum: a sign flip or a dropped line in `total`
- side rules: STT charged on BUY, stamp charged on SELL
- per-leg brokerage: brokerage on every partial fill, or never
- GST base: GST computed on STT/stamp, or on unrounded lines
- monotonicity: a rate applied to the wrong turnover (e.g. per-lot instead of per-rupee)
- exchange: SENSEX at the NSE rate, or the legacy flat rate moving
"""

import os
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ledger import Ledger
from ledger.charges import exchange_for, load_rates, order_charges

settings.register_profile("ci", max_examples=300, derandomize=True, deadline=500)
settings.register_profile("nightly", max_examples=5000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

CHARGES = Path(__file__).resolve().parents[3] / "config" / "charges.yaml"
RATES = load_rates(CHARGES, by_exchange=True)
FLAT = load_rates(CHARGES)
LINES = ("brokerage", "stt", "exchange", "sebi", "stamp", "gst")

sides = st.sampled_from(["BUY", "SELL"])
qtys = st.integers(min_value=0, max_value=50_000)
prices = st.decimals(min_value="0", max_value="5000", places=2).map(float)  # premiums in paise
exchanges = st.sampled_from([None, "NSE", "BSE"])


def paise(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def rates_for(exchange):
    return FLAT if exchange is None else RATES


@given(sides, qtys, prices, exchanges, st.booleans())
def test_every_line_non_negative_and_total_is_their_sum(side, qty, price, exchange, first):
    ch = order_charges(side, qty, price, rates_for(exchange), include_brokerage=first, exchange=exchange)
    assert all(ch[k] >= 0 for k in LINES)
    assert Decimal(str(ch["total"])) == sum(Decimal(str(ch[k])) for k in LINES)


@given(sides, qtys, prices, exchanges)
def test_stt_only_on_sell_stamp_only_on_buy(side, qty, price, exchange):
    r = rates_for(exchange)
    ch = order_charges(side, qty, price, r, exchange=exchange)
    turnover = Decimal(qty) * Decimal(str(price))
    if side == "SELL":
        assert ch["stamp"] == 0.0
        assert Decimal(str(ch["stt"])) == paise(turnover * Decimal(str(r["stt_sell_premium_frac"])))
    else:
        assert ch["stt"] == 0.0
        assert Decimal(str(ch["stamp"])) == paise(turnover * Decimal(str(r["stamp_duty_buy_frac"])))


@given(sides, qtys, prices, exchanges)
def test_exchange_and_sebi_lines_are_rate_times_turnover_to_the_paisa(side, qty, price, exchange):
    r = rates_for(exchange)
    ch = order_charges(side, qty, price, r, exchange=exchange)
    turnover = Decimal(qty) * Decimal(str(price))
    frac = r["exchange_txn_frac"] if exchange is None else r["exchange_txn_frac_by_exchange"][exchange]
    assert Decimal(str(ch["exchange"])) == paise(turnover * Decimal(str(frac)))
    assert Decimal(str(ch["sebi"])) == paise(turnover * Decimal(str(r["sebi_fee_frac"])))


@given(sides, qtys, prices, exchanges, st.booleans())
def test_gst_is_18_percent_of_rounded_brokerage_exchange_sebi(side, qty, price, exchange, first):
    r = rates_for(exchange)
    ch = order_charges(side, qty, price, r, include_brokerage=first, exchange=exchange)
    base = sum(Decimal(str(ch[k])) for k in ("brokerage", "exchange", "sebi"))
    assert Decimal(str(ch["gst"])) == paise(base * Decimal(str(r["gst_frac"])))


@given(qtys, prices, exchanges)
def test_brokerage_is_per_executed_order_leg(qty, price, exchange):
    r = rates_for(exchange)
    buy = order_charges("BUY", qty, price, r, exchange=exchange)
    sell = order_charges("SELL", qty, price, r, exchange=exchange)
    later_fill = order_charges("BUY", qty, price, r, include_brokerage=False, exchange=exchange)
    assert buy["brokerage"] == sell["brokerage"] == r["brokerage_per_order_inr"] == 20.0
    assert buy["brokerage"] + sell["brokerage"] == 40.0  # round trip = 2 orders
    assert later_fill["brokerage"] == 0.0


@given(sides, qtys, qtys, prices, prices, exchanges)
def test_every_line_is_monotone_in_qty_and_price(side, q1, q2, p1, p2, exchange):
    r = rates_for(exchange)
    lo = order_charges(side, min(q1, q2), min(p1, p2), r, exchange=exchange)
    hi = order_charges(side, max(q1, q2), max(p1, p2), r, exchange=exchange)
    assert all(lo[k] <= hi[k] for k in (*LINES, "total", "turnover"))


@given(sides, qtys, prices)
def test_bse_never_above_nse_and_flat_rate_is_the_legacy_one(side, qty, price):
    bse = order_charges(side, qty, price, RATES, exchange="BSE")
    nse = order_charges(side, qty, price, RATES, exchange="NSE")
    flat = order_charges(side, qty, price, FLAT)
    assert bse["exchange"] <= flat["exchange"] <= nse["exchange"]
    assert order_charges(side, qty, price, RATES) == flat  # no exchange given = legacy numbers


def test_rates_and_exchange_map_pinned():
    assert FLAT["exchange_txn_frac"] == 0.0003503  # legacy: unchanged by PR-B
    assert RATES["exchange_txn_frac_by_exchange"] == {"NSE": 0.0003553, "BSE": 0.000325}
    assert set(FLAT) == {"brokerage_per_order_inr", "stt_sell_premium_frac", "exchange_txn_frac",
                         "sebi_fee_frac", "stamp_duty_buy_frac", "gst_frac"}
    assert exchange_for("SENSEX 82000 CE", RATES) == "BSE" == exchange_for("BANKEX", RATES)
    assert exchange_for("NIFTY-CE", RATES) == "NSE" == exchange_for("BANKNIFTY 55000 PE", RATES)
    assert exchange_for("SENSEX 82000 CE", FLAT) is None
    with pytest.raises(ValueError):
        exchange_for("CRUDEOIL 6000 CE", RATES)


def _round_trip(led, symbol):
    for cid, side, purpose, px in (("E", "BUY", "ENTRY", 400.0), ("X", "SELL", "EXIT", 410.0)):
        row = {"client_order_id": cid, "broker": "paper", "mode": "paper", "symbol": symbol, "instrument_id": "1",
               "side": side, "qty": 500, "order_type": "MARKET", "decision_price": px, "purpose": purpose,
               "filled_qty": 0, "exit_reason": "TIME_EXIT" if purpose == "EXIT" else None}
        led.record_order(row, "NEW", "SUBMITTED", "test", "2026-09-28T10:00:00+05:30")
        trade_id = led.record_fill(cid, 500, px, "2026-09-28T10:00:00+05:30")
    return led.trade(trade_id)


def test_ledger_charges_sensex_at_bse_only_with_per_exchange_rates():
    flat, per_ex = Ledger(":memory:", rates=FLAT), Ledger(":memory:", rates=RATES)
    try:
        t_flat, t_bse = _round_trip(flat, "SENSEX 82000 CE"), _round_trip(per_ex, "SENSEX 82000 CE")
    finally:
        flat.close()
        per_ex.close()
    expected = sum(order_charges(s, 500, p, RATES, exchange="BSE")["total"] for s, p in (("BUY", 400.0), ("SELL", 410.0)))
    assert t_bse["charges"] == round(expected, 2)
    assert t_bse["charges"] < t_flat["charges"]  # BSE 0.0325% < legacy flat 0.03503%
