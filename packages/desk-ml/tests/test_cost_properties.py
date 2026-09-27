"""Property tests for round-trip paper charges: legacy `groww_round_trip_charges` and the realistic
per-leg model (`desk_ml.costs.realistic_charges`, one BUY + one SELL through ledger.charges).

Mutants these catch: STT on the buy premium, stamp on the sell premium, brokerage once per round
trip instead of per leg, GST on STT/stamp, SENSEX at the NSE rate, a non-monotone rate, fill
rounding in the trader's favour, and a realistic/legacy gap wider than the documented paise.
"""

import os

from hypothesis import given, settings
from hypothesis import strategies as st

from desk_ml import costs
from desk_ml.groww_costs import groww_round_trip_charges

settings.register_profile("ci", max_examples=300, derandomize=True, deadline=500)
settings.register_profile("nightly", max_examples=5000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

CFG = costs.load_config()
FLAT_CFG = {**CFG, "exchange_fees": "nse_flat"}
LINES = ("brokerage_inr", "gst_inr", "stt_inr", "exchange_inr", "sebi_inr", "stamp_inr", "charges_inr")
unds = st.sampled_from(["NIFTY", "BANKNIFTY", "SENSEX"])
qtys = st.integers(min_value=1, max_value=50_000)
prices = st.integers(min_value=1, max_value=100_000).map(lambda n: round(n * 0.05, 2))  # on-tick premiums


@given(unds, qtys, prices, prices)
def test_realistic_round_trip_non_negative_and_two_brokerage_legs(und, qty, buy, sell):
    ch = costs.realistic_charges(und, qty, buy, sell, CFG)
    assert all(ch[k] >= 0 for k in LINES)
    assert ch["brokerage_inr"] == 40.0 and ch["n_executed_orders"] == 2
    assert round(sum(ch[k] for k in LINES[:-1]), 2) == ch["charges_inr"]
    assert ch["stt_inr"] == costs.realistic_charges(und, qty, 999.95, sell, CFG)["stt_inr"]  # STT: sell leg only
    assert ch["stamp_inr"] == costs.realistic_charges(und, qty, buy, 999.95, CFG)["stamp_inr"]  # stamp: buy leg only


@given(unds, qtys, qtys, prices, prices, prices, prices)
def test_realistic_round_trip_monotone(und, q1, q2, b1, b2, s1, s2):
    lo = costs.realistic_charges(und, min(q1, q2), min(b1, b2), min(s1, s2), CFG)
    hi = costs.realistic_charges(und, max(q1, q2), max(b1, b2), max(s1, s2), CFG)
    assert all(lo[k] <= hi[k] for k in LINES)


@given(qtys, prices, prices)
def test_sensex_pays_less_exchange_fee_than_nifty(qty, buy, sell):
    sx = costs.realistic_charges("SENSEX", qty, buy, sell, CFG)
    nf = costs.realistic_charges("NIFTY", qty, buy, sell, CFG)
    assert sx["exchange"] == "BSE" and nf["exchange"] == "NSE"
    assert sx["exchange_inr"] <= nf["exchange_inr"]
    assert {k: v for k, v in sx.items() if k not in ("exchange_inr", "gst_inr", "charges_inr", "exchange")} == \
        {k: v for k, v in nf.items() if k not in ("exchange_inr", "gst_inr", "charges_inr", "exchange")}


@given(unds, qtys, prices, prices)
def test_legacy_round_trip_non_negative_and_monotone_in_qty(und, qty, buy, sell):
    one = groww_round_trip_charges(exit_premium=sell, entry_premium=buy, qty=qty, filled=True)
    two = groww_round_trip_charges(exit_premium=sell, entry_premium=buy, qty=qty + 1, filled=True)
    assert all(one[k] >= 0 for k in LINES) and one["brokerage_inr"] == 40.0
    assert all(one[k] <= two[k] for k in LINES)


@given(unds, qtys, prices, prices)
def test_realistic_nse_flat_matches_legacy_within_documented_paise(und, qty, buy, sell):
    """D6: legacy rounds round-trip components; the ledger rounds per order. <= 1 paisa per line."""
    real = costs.realistic_charges(und, qty, buy, sell, FLAT_CFG)
    legacy = groww_round_trip_charges(exit_premium=sell, entry_premium=buy, qty=qty, filled=True)
    for k in ("exchange_inr", "sebi_inr", "gst_inr"):
        assert abs(real[k] - legacy[k]) <= 0.0201  # two orders, each off by at most half a paisa per line
    assert abs(real["charges_inr"] - legacy["charges_inr"]) <= 0.06


@given(st.floats(min_value=0.05, max_value=5000, allow_nan=False), st.floats(min_value=0, max_value=5))
def test_fills_are_on_tick_and_never_in_the_traders_favour(px, slip):
    buy, sell = costs.entry_fill_price(px, slip), costs.exit_fill_price(px, slip)
    for fill in (buy, sell):
        assert abs(fill / 0.05 - round(fill / 0.05)) < 1e-6
    assert buy >= px + slip - 1e-9
    assert sell <= max(0.05, px - slip) + 1e-9 and sell >= 0.05
