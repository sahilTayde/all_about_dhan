"""Charges calculator against a hand-computed NIFTY option round trip."""

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from ledger.charges import load_rates, order_charges

_CHARGES_SRC = Path(__file__).resolve().parents[1] / "src" / "ledger" / "charges.py"

RATES = load_rates(Path(__file__).resolve().parents[3] / "config" / "charges.yaml")


def test_config_rates_are_the_desk_cost_model():
    # Same numbers as packages/desk-ml/src/desk_ml/groww_costs.py
    assert RATES == {
        "brokerage_per_order_inr": 20.0,
        "stt_sell_premium_frac": 0.0015,
        "exchange_txn_frac": 0.000355299,
        "ipft_frac": 0.000000001,
        "sebi_fee_frac": 0.000001,
        "stamp_duty_buy_frac": 0.00003,
        "gst_frac": 0.18,
    }


def test_hand_computed_round_trip():
    # 1 lot NIFTY CE (65 qty): buy @ 100, sell @ 130. NSE/FA/73061 txn 0.0355299%.
    # BUY  turnover 6500:  brokerage 20.00; exchange 6500*0.0355299% = 2.3094435 -> 2.31;
    #      IPFT 6500*0.0000001% -> 0.00; SEBI 6500*0.0001% = 0.0065 -> 0.01;
    #      stamp 6500*0.003% = 0.195 -> 0.20; STT 0;
    #      GST 18% * (20 + 2.31 + 0.01 + 0.00 = 22.32) = 4.0176 -> 4.02.   Total 26.54
    # SELL turnover 8450:  brokerage 20.00; exchange 8450*0.0355299% = 3.00227655 -> 3.00;
    #      IPFT 0.00; SEBI 0.00845 -> 0.01; STT 8450*0.15% = 12.675 -> 12.68; stamp 0;
    #      GST 18% * (20 + 3.00 + 0.01 + 0.00 = 23.01) = 4.1418 -> 4.14.   Total 39.83
    # Round trip 66.37. Gross (130-100)*65 = 1950. Net 1883.63.
    buy = order_charges("BUY", 65, 100.0, RATES)
    sell = order_charges("SELL", 65, 130.0, RATES)
    assert buy == {
        "turnover": 6500.0, "brokerage": 20.0, "stt": 0.0, "exchange": 2.31,
        "ipft": 0.0, "sebi": 0.01, "stamp": 0.2, "gst": 4.02, "total": 26.54,
    }
    assert sell == {
        "turnover": 8450.0, "brokerage": 20.0, "stt": 12.68, "exchange": 3.00,
        "ipft": 0.0, "sebi": 0.01, "stamp": 0.0, "gst": 4.14, "total": 39.83,
    }
    assert round(buy["total"] + sell["total"], 2) == 66.37
    assert round((130 - 100) * 65 - (buy["total"] + sell["total"]), 2) == 1883.63


def test_second_fill_of_same_order_has_no_brokerage():
    part = order_charges("BUY", 65, 100.0, RATES, include_brokerage=False)
    assert part["brokerage"] == 0.0
    assert part["gst"] == 0.42  # 18% * (0 + 2.31 + 0.01 + 0.00) = 0.4176


def test_bad_side_raises():
    with pytest.raises(ValueError):
        order_charges("HOLD", 65, 100.0, RATES)


# Previous float fixture values from test_hand_computed_round_trip (paise-rounded).
_PREVIOUS_BUY = {
    "turnover": 6500.0,
    "brokerage": 20.0,
    "stt": 0.0,
    "exchange": 2.31,
    "ipft": 0.0,
    "sebi": 0.01,
    "stamp": 0.2,
    "gst": 4.02,
    "total": 26.54,
}
_PREVIOUS_SELL = {
    "turnover": 8450.0,
    "brokerage": 20.0,
    "stt": 12.68,
    "exchange": 3.00,
    "ipft": 0.0,
    "sebi": 0.01,
    "stamp": 0.0,
    "gst": 4.14,
    "total": 39.83,
}


def test_charges_return_decimal_equals_fixture_paisa() -> None:
    """order_charges returns Decimal end to end; paisa-equal to the previous float fixtures."""
    paise = Decimal("0.01")
    buy = order_charges("BUY", 65, 100.0, RATES)
    sell = order_charges("SELL", 65, 130.0, RATES)
    assert buy.keys() == _PREVIOUS_BUY.keys()
    assert sell.keys() == _PREVIOUS_SELL.keys()
    for key, prev in _PREVIOUS_BUY.items():
        assert isinstance(buy[key], Decimal), f"{key} must be Decimal, got {type(buy[key])}"
        assert Decimal(str(buy[key])).quantize(paise) == Decimal(str(prev)).quantize(paise)
    for key, prev in _PREVIOUS_SELL.items():
        assert isinstance(sell[key], Decimal), f"{key} must be Decimal, got {type(sell[key])}"
        assert Decimal(str(sell[key])).quantize(paise) == Decimal(str(prev)).quantize(paise)
    # Decimal price in, Decimal out (no float round-trip).
    priced = order_charges("BUY", 65, Decimal("100.00"), RATES)
    assert all(isinstance(v, Decimal) for v in priced.values())
    assert priced["total"].quantize(paise) == Decimal("26.54")


def test_charges_compiles_under_python39_grammar() -> None:
    """CI-independent: Mac desk is CPython 3.9.25; typing.Self is 3.11+ ImportError."""
    text = _CHARGES_SRC.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(_CHARGES_SRC), feature_version=(3, 9))
    assert tree.body, "charges.py parsed empty under the 3.9 grammar"
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "") == "typing":
            names = {alias.name for alias in node.names}
            assert "Self" not in names, "from typing import Self fails on CPython 3.9"
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "Self"
            and isinstance(node.value, ast.Name)
            and node.value.id == "typing"
        ):
            raise AssertionError("typing.Self is not importable on CPython 3.9")
    import ledger.charges

    assert ledger.charges.Paisa("1.00") == Decimal("1.00")
