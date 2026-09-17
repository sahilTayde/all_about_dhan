"""Groww F&O brokerage + option STT on filled paper round-trips.

02/09: this is a named HYPOTHESIS/VERIFY overlay for the paper board.
It does **not** make a MIX CANDIDATE. Unfilled CANCELLED tickets: ₹0.

SOURCE (web, not an NSE circular in-repo):
- Groww F&O brokerage: ₹20 per executed order (groww.in help).
- STT on option sale: 0.15% of sell premium from 1 Apr 2026 (Budget 2026 /
  Groww blog). Older tables (0.05% / 0.10%) conflict — keep VERIFY.
- GST 18% applied on Groww brokerage only. Exchange + SEBI + stamp omitted
  (still UNKNOWN).
"""

from __future__ import annotations

from typing import Any, Optional

GROWW_BROKERAGE_PER_ORDER_INR = 20.0
GST_ON_BROKERAGE_FRAC = 0.18
# Sell-side option premium STT from 1 Apr 2026. VERIFY vs older slabs.
STT_OPTION_SELL_FRAC = 0.0015
EXECUTED_ORDERS_ROUND_TRIP = 2
COST_NAME = "GROWW_FO_20_PLUS_STT_015"
COST_LAYER = "HYPOTHESIS"
STATUTORY_STATUS = "VERIFY"


def as_dict() -> dict[str, Any]:
    return {
        "name": COST_NAME,
        "layer": COST_LAYER,
        "statutory_status": STATUTORY_STATUS,
        "brokerage_per_executed_order_inr": GROWW_BROKERAGE_PER_ORDER_INR,
        "executed_orders_round_trip": EXECUTED_ORDERS_ROUND_TRIP,
        "gst_on_brokerage_frac": GST_ON_BROKERAGE_FRAC,
        "stt_option_sell_frac": STT_OPTION_SELL_FRAC,
        "omitted": ["exchange_txn", "sebi", "stamp_buy", "half_spread"],
        "cite": [
            "https://groww.in/help (F&O brokerage ₹20/order)",
            "Budget 2026 option STT 0.15% sell premium from 1 Apr 2026 (VERIFY)",
        ],
        "note": (
            "Filled buy+sell = 2 Groww orders. STT on exit premium × qty. "
            "CANCELLED unfilled = ₹0 charges. Cannot CANDIDATE from this board."
        ),
    }


def groww_round_trip_charges(
    *,
    exit_premium: float,
    qty: Optional[int],
    filled: bool,
) -> dict[str, Any]:
    if not filled:
        return {
            "brokerage_inr": 0.0,
            "gst_inr": 0.0,
            "stt_inr": 0.0,
            "charges_inr": 0.0,
            "slippage_inr": 0.0,
            "n_executed_orders": 0,
            "stt_status": "N/A_UNFILLED",
        }
    brokerage = GROWW_BROKERAGE_PER_ORDER_INR * EXECUTED_ORDERS_ROUND_TRIP
    gst = round(brokerage * GST_ON_BROKERAGE_FRAC, 2)
    units = int(qty) if qty is not None and int(qty) > 0 else 0
    if units <= 0 or exit_premium <= 0:
        stt = 0.0
        stt_status = "DATA_INSUFFICIENT_QTY_OR_EXIT"
    else:
        stt = round(float(exit_premium) * units * STT_OPTION_SELL_FRAC, 2)
        stt_status = STATUTORY_STATUS
    charges = round(brokerage + gst + stt, 2)
    return {
        "brokerage_inr": round(brokerage, 2),
        "gst_inr": gst,
        "stt_inr": stt,
        "charges_inr": charges,
        "n_executed_orders": EXECUTED_ORDERS_ROUND_TRIP,
        "stt_status": stt_status,
    }


def net_pnl_inr(*, gross_inr: Optional[float], charges_inr: float) -> Optional[float]:
    if gross_inr is None:
        return None
    return round(float(gross_inr) - float(charges_inr), 2)


def breakeven_premium(*, entry: float, qty: Optional[int]) -> float:
    """Exit premium that covers Groww+GST+STT on a filled long. PAPER HYPOTHESIS."""
    ch = groww_round_trip_charges(exit_premium=float(entry), qty=qty, filled=True)
    units = int(qty) if qty is not None and int(qty) > 0 else 0
    if units <= 0:
        return float(entry)
    return round(float(entry) + float(ch["charges_inr"]) / units, 4)
