"""Groww F&O brokerage + statutory option charges on filled paper round-trips.

02/09: named HYPOTHESIS/VERIFY overlay for the paper board.
It does **not** make a MIX CANDIDATE. Unfilled CANCELLED tickets: ₹0.

SOURCE (web, not an NSE circular in-repo):
- Groww F&O brokerage: ₹20 per executed order (groww.in help).
- STT on option sale: 0.15% of sell premium from 1 Apr 2026 (Budget 2026).
- Exchange txn (options): 0.03503% of premium, both legs (VERIFY vs NSE circular).
- SEBI turnover: 0.0001% of premium, both legs.
- Stamp duty: 0.003% of buy premium only (Finance Act 2019 uniform).
- GST 18% on brokerage + exchange + SEBI (not on STT/stamp).
- IPF / clearing / half-spread still UNKNOWN.
"""

from __future__ import annotations

from typing import Any, Optional

GROWW_BROKERAGE_PER_ORDER_INR = 20.0
GST_ON_BROKERAGE_FRAC = 0.18
# Sell-side option premium STT from 1 Apr 2026. VERIFY vs older slabs.
STT_OPTION_SELL_FRAC = 0.0015
# Options premium turnover. VERIFY vs current NSE/BSE circular.
EXCHANGE_TXN_OPTIONS_FRAC = 0.0003503
SEBI_TURNOVER_FRAC = 0.000001
STAMP_OPTIONS_BUY_FRAC = 0.00003
EXECUTED_ORDERS_ROUND_TRIP = 2
COST_NAME = "GROWW_FO_20_PLUS_STATUTORY_OPTIONS"
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
        "exchange_txn_options_frac": EXCHANGE_TXN_OPTIONS_FRAC,
        "sebi_turnover_frac": SEBI_TURNOVER_FRAC,
        "stamp_options_buy_frac": STAMP_OPTIONS_BUY_FRAC,
        "omitted": ["ipf", "clearing", "half_spread", "bse_vs_nse_split"],
        "cite": [
            "https://groww.in/help (F&O brokerage ₹20/order; statutory passed through)",
            "Budget 2026 option STT 0.15% sell premium from 1 Apr 2026 (VERIFY)",
            "NSE/BSE options txn + SEBI 0.0001% + stamp 0.003% buy (VERIFY)",
        ],
        "note": (
            "Filled buy+sell = 2 Groww orders. STT on exit premium × qty. "
            "Exchange+SEBI on both premium legs. Stamp on buy premium. "
            "GST 18% on brokerage+exchange+SEBI. CANCELLED unfilled = ₹0. "
            "Cannot CANDIDATE from this board."
        ),
    }


def _zero_charges(*, filled: bool) -> dict[str, Any]:
    return {
        "brokerage_inr": 0.0,
        "gst_inr": 0.0,
        "stt_inr": 0.0,
        "exchange_inr": 0.0,
        "sebi_inr": 0.0,
        "stamp_inr": 0.0,
        "charges_inr": 0.0,
        "slippage_inr": 0.0,
        "n_executed_orders": 0 if not filled else EXECUTED_ORDERS_ROUND_TRIP,
        "stt_status": "N/A_UNFILLED" if not filled else "DATA_INSUFFICIENT_QTY_OR_EXIT",
    }


def groww_round_trip_charges(
    *,
    exit_premium: float,
    qty: Optional[int],
    filled: bool,
    entry_premium: Optional[float] = None,
) -> dict[str, Any]:
    if not filled:
        return _zero_charges(filled=False)
    units = int(qty) if qty is not None and int(qty) > 0 else 0
    sell_px = float(exit_premium)
    try:
        buy_px = float(entry_premium) if entry_premium is not None else sell_px
    except (TypeError, ValueError):
        buy_px = sell_px
    if units <= 0 or sell_px <= 0 or buy_px <= 0:
        row = _zero_charges(filled=True)
        row["brokerage_inr"] = round(GROWW_BROKERAGE_PER_ORDER_INR * EXECUTED_ORDERS_ROUND_TRIP, 2)
        row["gst_inr"] = round(row["brokerage_inr"] * GST_ON_BROKERAGE_FRAC, 2)
        row["charges_inr"] = round(row["brokerage_inr"] + row["gst_inr"], 2)
        return row
    buy_turn = buy_px * units
    sell_turn = sell_px * units
    brokerage = GROWW_BROKERAGE_PER_ORDER_INR * EXECUTED_ORDERS_ROUND_TRIP
    exchange = round((buy_turn + sell_turn) * EXCHANGE_TXN_OPTIONS_FRAC, 2)
    sebi = round((buy_turn + sell_turn) * SEBI_TURNOVER_FRAC, 2)
    stamp = round(buy_turn * STAMP_OPTIONS_BUY_FRAC, 2)
    gst = round((brokerage + exchange + sebi) * GST_ON_BROKERAGE_FRAC, 2)
    stt = round(sell_turn * STT_OPTION_SELL_FRAC, 2)
    charges = round(brokerage + gst + stt + exchange + sebi + stamp, 2)
    return {
        "brokerage_inr": round(brokerage, 2),
        "gst_inr": gst,
        "stt_inr": stt,
        "exchange_inr": exchange,
        "sebi_inr": sebi,
        "stamp_inr": stamp,
        "charges_inr": charges,
        "n_executed_orders": EXECUTED_ORDERS_ROUND_TRIP,
        "stt_status": STATUTORY_STATUS,
    }


def net_pnl_inr(*, gross_inr: Optional[float], charges_inr: float) -> Optional[float]:
    if gross_inr is None:
        return None
    return round(float(gross_inr) - float(charges_inr), 2)


def breakeven_premium(*, entry: float, qty: Optional[int]) -> float:
    """Exit premium that covers Groww+statutory on a filled long. PAPER HYPOTHESIS."""
    ch = groww_round_trip_charges(
        exit_premium=float(entry),
        entry_premium=float(entry),
        qty=qty,
        filled=True,
    )
    units = int(qty) if qty is not None and int(qty) > 0 else 0
    if units <= 0:
        return float(entry)
    return round(float(entry) + float(ch["charges_inr"]) / units, 4)
