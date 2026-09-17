"""Groww + STT paper overlay. HYPOTHESIS/VERIFY. NO_PROMOTE."""

from desk_ml.groww_costs import groww_round_trip_charges, net_pnl_inr


def test_unfilled_zero_charges() -> None:
    row = groww_round_trip_charges(exit_premium=200.0, qty=65, filled=False)
    assert row["charges_inr"] == 0.0
    assert row["brokerage_inr"] == 0.0
    assert row["gst_inr"] == 0.0
    assert row["stt_inr"] == 0.0
    assert row["slippage_inr"] == 0.0
    assert row["n_executed_orders"] == 0
    assert net_pnl_inr(gross_inr=0.0, charges_inr=row["charges_inr"]) == 0.0


def test_filled_round_trip_brokerage_gst_stt() -> None:
    # NIFTY 65 qty, sell premium 100 → STT 0.15% × 6500 = 9.75
    row = groww_round_trip_charges(exit_premium=100.0, qty=65, filled=True)
    assert row["n_executed_orders"] == 2
    assert row["brokerage_inr"] == 40.0
    assert row["gst_inr"] == 7.2
    assert row["stt_inr"] == 9.75
    assert row["charges_inr"] == 56.95
    assert net_pnl_inr(gross_inr=200.0, charges_inr=row["charges_inr"]) == 143.05


def test_small_gross_can_flip_to_net_loss() -> None:
    row = groww_round_trip_charges(exit_premium=80.0, qty=65, filled=True)
    net = net_pnl_inr(gross_inr=40.0, charges_inr=row["charges_inr"])
    assert net is not None
    assert net < 0


def test_breakeven_premium_covers_charges() -> None:
    from desk_ml.groww_costs import breakeven_premium, groww_round_trip_charges

    be = breakeven_premium(entry=100.0, qty=65)
    ch = groww_round_trip_charges(exit_premium=100.0, qty=65, filled=True)
    assert be == round(100.0 + ch["charges_inr"] / 65, 4)
    assert be > 100.0
    assert breakeven_premium(entry=100.0, qty=None) == 100.0
