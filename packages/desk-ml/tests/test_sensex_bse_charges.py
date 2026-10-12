"""SENSEX desk charges ran ~Rs 10/trade above the BSE-rate formula: groww_round_trip_charges used the NSE
txn rate (0.000355299 + IPFT) for every index. config/paper_costs.yaml exchange_fees: per_exchange."""

from __future__ import annotations

from pathlib import Path

import yaml

from desk_ml import groww_costs as gc, research_rules as rr

REPO = Path(__file__).resolve().parents[3]


def test_bse_rate_matches_config() -> None:
    rates = yaml.safe_load((REPO / "config" / "charges.yaml").read_text())["exchange_txn_frac_by_exchange"]
    assert gc.BSE_EXCHANGE_TXN_OPTIONS_FRAC == rates["BSE"]
    assert yaml.safe_load((REPO / "config" / "paper_costs.yaml").read_text())["exchange_fees"] == "per_exchange"


def test_sensex_uses_bse_nifty_unchanged() -> None:
    sx = gc.groww_round_trip_charges(entry_premium=427.5, exit_premium=420.0, qty=200, filled=True, underlying="SENSEX")
    assert sx["exchange_inr"] == round((427.5 + 420.0) * 200 * 0.000325, 2) and sx["ipft_inr"] == 0.0
    old = gc.groww_round_trip_charges(entry_premium=427.5, exit_premium=420.0, qty=200, filled=True)
    assert old == gc.groww_round_trip_charges(entry_premium=427.5, exit_premium=420.0, qty=200, filled=True, underlying="NIFTY")
    diff_desk = round((old["charges_inr"] - sx["charges_inr"]) * rr.COST_MULT, 2)
    assert 8.0 < diff_desk < 11.0  # the ~Rs 10/trade overcharge seen on the desk (1.5x cost fixture)


def test_research_rules_cost_row_passes_underlying() -> None:
    a = rr._cost_row(entry=427.5, exit_px=420.0, qty=200, filled=True, underlying="SENSEX")
    b = rr._cost_row(entry=427.5, exit_px=420.0, qty=200, filled=True, underlying="NIFTY")
    assert a["charges_inr"] < b["charges_inr"]
