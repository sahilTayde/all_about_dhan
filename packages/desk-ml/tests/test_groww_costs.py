"""Dhan + NSE statutory paper overlay. HYPOTHESIS / not contract-note. NO_PROMOTE."""

from desk_ml.groww_costs import groww_round_trip_charges, net_pnl_inr


def test_unfilled_zero_charges() -> None:
    row = groww_round_trip_charges(exit_premium=200.0, qty=65, filled=False)
    assert row["charges_inr"] == 0.0
    assert row["brokerage_inr"] == 0.0
    assert row["gst_inr"] == 0.0
    assert row["stt_inr"] == 0.0
    assert row["exchange_inr"] == 0.0
    assert row["ipft_inr"] == 0.0
    assert row["sebi_inr"] == 0.0
    assert row["stamp_inr"] == 0.0
    assert row["slippage_inr"] == 0.0
    assert row["n_executed_orders"] == 0
    assert net_pnl_inr(gross_inr=0.0, charges_inr=row["charges_inr"]) == 0.0


def test_filled_round_trip_includes_exchange_sebi_stamp() -> None:
    # NIFTY 65 qty, buy=sell 100. Brokerage 40. STT 0.15% × 6500 = 9.75
    # Exch 0.0355299% × 13000 = 4.618887 → 4.62; IPFT 0.0000001% × 13000 → 0.00;
    # SEBI 0.0001% × 13000; stamp 0.003% × 6500; GST 18% on brk+exch+sebi+ipft.
    row = groww_round_trip_charges(exit_premium=100.0, entry_premium=100.0, qty=65, filled=True)
    assert row["n_executed_orders"] == 2
    assert row["brokerage_inr"] == 40.0
    assert row["stt_inr"] == 9.75
    assert row["exchange_inr"] == 4.62
    assert row["ipft_inr"] == 0.0
    assert row["sebi_inr"] == 0.01
    assert row["stamp_inr"] == 0.20
    assert row["gst_inr"] == 8.03
    assert row["charges_inr"] == 62.61
    assert row["charges_inr"] > 62.53  # old ₹3,503/crore fixture understated txn
    assert net_pnl_inr(gross_inr=200.0, charges_inr=row["charges_inr"]) == 137.39


def test_ten_lots_statutory_scales_with_premium() -> None:
    one = groww_round_trip_charges(exit_premium=150.0, entry_premium=149.7, qty=65, filled=True)
    ten = groww_round_trip_charges(exit_premium=150.0, entry_premium=149.7, qty=650, filled=True)
    assert ten["brokerage_inr"] == one["brokerage_inr"] == 40.0
    assert ten["stt_inr"] == round(150.0 * 650 * 0.0015, 2)
    assert abs(ten["stt_inr"] - one["stt_inr"] * 10) < 0.1
    assert ten["exchange_inr"] > one["exchange_inr"]
    assert ten["charges_inr"] > one["charges_inr"] * 1.5


def test_small_gross_can_flip_to_net_loss() -> None:
    row = groww_round_trip_charges(exit_premium=80.0, qty=65, filled=True)
    net = net_pnl_inr(gross_inr=40.0, charges_inr=row["charges_inr"])
    assert net is not None
    assert net < 0


def test_as_dict_is_dhan_nse_sourced_not_contract_note() -> None:
    from desk_ml.groww_costs import EXCHANGE_TXN_OPTIONS_FRAC, IPFT_OPTIONS_FRAC, as_dict

    meta = as_dict()
    assert meta["statutory_status"] == "DHAN_NSE_SOURCED_NOT_CONTRACT_NOTE"
    assert EXCHANGE_TXN_OPTIONS_FRAC == 0.000355299
    assert IPFT_OPTIONS_FRAC == 0.000000001
    assert "clearing" in meta["omitted"]
    assert "ipf" not in meta["omitted"]
    assert meta["ipft_options_frac"] == IPFT_OPTIONS_FRAC


def test_ipft_appears_on_large_premium_turnover() -> None:
    # 0.000000001 × (1_000_000 × 100 × 2) = ₹0.20; GST includes IPFT (qty=65 rounds IPFT to ₹0.00).
    row = groww_round_trip_charges(exit_premium=100.0, entry_premium=100.0, qty=1_000_000, filled=True)
    assert row["ipft_inr"] == 0.20
    gst_without_ipft = round((row["brokerage_inr"] + row["exchange_inr"] + row["sebi_inr"]) * 0.18, 2)
    assert row["gst_inr"] == round((row["brokerage_inr"] + row["exchange_inr"] + row["sebi_inr"] + 0.20) * 0.18, 2)
    assert row["gst_inr"] != gst_without_ipft


def test_breakeven_premium_covers_charges() -> None:
    from desk_ml.groww_costs import breakeven_premium, groww_round_trip_charges

    be = breakeven_premium(entry=100.0, qty=65)
    ch = groww_round_trip_charges(exit_premium=100.0, entry_premium=100.0, qty=65, filled=True)
    assert be == round(100.0 + ch["charges_inr"] / 65, 4)
    assert be > 100.0
    assert breakeven_premium(entry=100.0, qty=None) == 100.0
