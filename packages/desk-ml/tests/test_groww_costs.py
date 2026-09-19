"""Groww + statutory paper overlay. HYPOTHESIS/VERIFY. NO_PROMOTE."""

from desk_ml.groww_costs import groww_round_trip_charges, net_pnl_inr


def test_unfilled_zero_charges() -> None:
    row = groww_round_trip_charges(exit_premium=200.0, qty=65, filled=False)
    assert row["charges_inr"] == 0.0
    assert row["brokerage_inr"] == 0.0
    assert row["gst_inr"] == 0.0
    assert row["stt_inr"] == 0.0
    assert row["exchange_inr"] == 0.0
    assert row["sebi_inr"] == 0.0
    assert row["stamp_inr"] == 0.0
    assert row["slippage_inr"] == 0.0
    assert row["n_executed_orders"] == 0
    assert net_pnl_inr(gross_inr=0.0, charges_inr=row["charges_inr"]) == 0.0


def test_filled_round_trip_includes_exchange_sebi_stamp() -> None:
    # NIFTY 65 qty, buy=sell 100. Brokerage 40. STT 0.15% × 6500 = 9.75
    # Exch 0.03503% × 13000; SEBI 0.0001% × 13000; stamp 0.003% × 6500; GST 18% on brk+exch+sebi.
    row = groww_round_trip_charges(exit_premium=100.0, entry_premium=100.0, qty=65, filled=True)
    assert row["n_executed_orders"] == 2
    assert row["brokerage_inr"] == 40.0
    assert row["stt_inr"] == 9.75
    assert row["exchange_inr"] == 4.55
    assert row["sebi_inr"] == 0.01
    assert row["stamp_inr"] == 0.20
    assert row["gst_inr"] == 8.02
    assert row["charges_inr"] == 62.53
    assert row["charges_inr"] > 56.95  # old Groww+GST-on-brokerage+STT only
    assert net_pnl_inr(gross_inr=200.0, charges_inr=row["charges_inr"]) == 137.47


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


def test_breakeven_premium_covers_charges() -> None:
    from desk_ml.groww_costs import breakeven_premium, groww_round_trip_charges

    be = breakeven_premium(entry=100.0, qty=65)
    ch = groww_round_trip_charges(exit_premium=100.0, entry_premium=100.0, qty=65, filled=True)
    assert be == round(100.0 + ch["charges_inr"] / 65, 4)
    assert be > 100.0
    assert breakeven_premium(entry=100.0, qty=None) == 100.0
