"""REG-12a-e: verified cost stack, lot size from master, depth/fcmeas, no legacy mode."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from brokers.factory import LiveBrokerDisabled, make_broker
from brokers.fills import (
    DEFAULT_TABLE,
    FillOrder,
    Quote,
    choose_fill,
    fcmeas_half_spread,
    flat_sensitivity,
)
from contracts.clock import SimClock
from contracts.instruments import India
from helpers import INST, NOW, REPO, make_decision, make_plan, make_router
from ledger.charges import load_rates, order_charges
from oms import Account, MemoryLedger, lot_size_for
from oms.router import load_cost_rates


def test_reg_12a_golden_contract_note_nse_and_bse() -> None:
    rates = load_rates(REPO / "config" / "charges.yaml", by_exchange=True)
    assert (
        rates["exchange_txn_frac_by_exchange"]["NSE"] == 0.0003553
    )  # IPFT included (K14)
    assert rates["exchange_txn_frac_by_exchange"]["BSE"] == 0.000325
    qty = India().lot_size("NIFTY") * 25
    for exchange in ("NSE", "BSE"):
        buy = order_charges("BUY", qty, 100.0, rates, exchange=exchange)
        sell = order_charges("SELL", qty, 100.0, rates, exchange=exchange)
        buy_base = buy["brokerage"] + buy["exchange"] + buy["sebi"]
        sell_base = sell["brokerage"] + sell["exchange"] + sell["sebi"]
        assert abs(buy["gst"] - round(buy_base * 0.18 + 1e-12, 2)) <= 0.01
        assert abs(sell["gst"] - round(sell_base * 0.18 + 1e-12, 2)) <= 0.01
        assert buy["stt"] == 0.0 and buy["stamp"] > 0
        assert sell["stamp"] == 0.0 and sell["stt"] > 0
        # GST must not sit on STT+stamp (K12)
        assert sell["gst"] < sell["stt"]


def test_reg_12b_every_fill_has_charges_row(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    store = MemoryLedger()
    rates = load_cost_rates(REPO / "config" / "charges.yaml")
    broker = make_broker(clock=clock)
    router = make_router(tmp_path, clock, broker=broker, store=store, rates=rates)
    order = router.submit(make_plan(), make_decision(), Account("founder"))
    clock.advance_by(timedelta(milliseconds=250))
    broker.on_depth(
        Quote(
            available_ts=clock.now(),
            bid=151.00,
            ask=151.20,
            ltp=151.10,
            instrument_id=INST,
        )
    )
    assert order.state.value == "FILLED"
    assert store.charges, "fill escaped the ledger"
    row = store.charges[0]
    assert row.charges_status == "FINAL"
    assert row.components["total"] > 0
    assert row.exchange == "NSE"


def test_reg_12c_lot_size_from_instrument_master() -> None:
    india = India()
    assert india.lot_size("NIFTY") == 65
    assert lot_size_for("NSE_FNO:NIFTY:2026-09-29:24400:CE") == india.lot_size("NIFTY")


def test_reg_12d_depth_vs_fcmeas_and_tod_table() -> None:
    morning = datetime(2026, 9, 28, 10, 0, tzinfo=NOW.tzinfo)
    noon = datetime(2026, 9, 28, 12, 0, tzinfo=NOW.tzinfo)
    late = datetime(2026, 9, 28, 15, 5, tzinfo=NOW.tzinfo)
    expected = {
        ("ATM", morning): 0.20,
        ("ATM", noon): 0.25,
        ("ATM", late): 0.30,
        ("ITM100", morning): 0.30,
        ("ITM100", noon): 0.35,
        ("ITM100", late): 0.40,
        ("ITM200", morning): 0.35,
        ("ITM200", noon): 0.40,
        ("ITM200", late): 0.45,
    }
    for (bucket, when), pts in expected.items():
        assert fcmeas_half_spread(bucket, when, DEFAULT_TABLE) == pts
    order = FillOrder(
        client_order_id="aad" + "d" * 24,
        side="BUY",
        order_type="MARKET",
        available_ts=morning,
        decision_ts=morning,
        lots=2,
        lot_size=65,
        instrument_id=INST,
        moneyness="ITM100",
    )
    q = Quote(
        available_ts=morning, bid=151.10, ask=151.35, ltp=151.20, instrument_id=INST
    )
    px, model = choose_fill(order, [q], 151.20, morning)  # type: ignore[misc]
    assert model == "depth"
    assert abs(px - 151.35) < 0.06
    no_depth, model2 = choose_fill(order, [], 151.20, morning)  # type: ignore[misc]
    assert model2 == "fcmeas"
    assert abs(no_depth - (151.20 + 0.30)) < 0.06
    assert abs(flat_sensitivity(151.20, "BUY") - 151.40) < 1e-9


def test_reg_12e_no_legacy_cost_model_path() -> None:
    clock = SimClock(NOW)
    broker = make_broker(clock=clock)
    assert broker.cost_model == "realistic"
    with pytest.raises(LiveBrokerDisabled):
        make_broker(mode="paper", clock=clock, cost_model="legacy")
    yaml_path = (
        Path(__file__).resolve().parents[2] / "config" / "v2" / "markets" / "india.yaml"
    )
    assert "cost_model: legacy" not in yaml_path.read_text(encoding="utf-8")
    assert "cost_model" not in yaml_path.read_text(encoding="utf-8")
