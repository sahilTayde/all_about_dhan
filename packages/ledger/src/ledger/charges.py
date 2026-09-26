"""Per-order charges for Indian index options. Rates live in config/charges.yaml."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import yaml

# This repo's config/charges.yaml (editable install), not the process CWD; CWD only as a fallback.
_REPO_CHARGES = Path(__file__).resolve().parents[4] / "config" / "charges.yaml"
DEFAULT_CHARGES_PATH = _REPO_CHARGES if _REPO_CHARGES.is_file() else Path("config/charges.yaml")
RATE_KEYS = (
    "brokerage_per_order_inr",
    "stt_sell_premium_frac",
    "exchange_txn_frac",
    "sebi_fee_frac",
    "stamp_duty_buy_frac",
    "gst_frac",
)
_PAISE = Decimal("0.01")


def load_rates(path: Path = DEFAULT_CHARGES_PATH) -> dict[str, float]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    missing = [k for k in RATE_KEYS if k not in data]
    if missing:
        raise ValueError(f"{path}: missing charge rates {missing}")
    return {k: float(data[k]) for k in RATE_KEYS}


def _d(x: Any) -> Decimal:
    return Decimal(str(x))


def _inr(x: Decimal) -> Decimal:
    return x.quantize(_PAISE, rounding=ROUND_HALF_UP)


def order_charges(
    side: str, qty: int, price: float, rates: dict[str, float], *, include_brokerage: bool = True
) -> dict[str, float]:
    """Charges for one executed order (or one fill of it).

    Each component is rounded to paise like a contract note line; GST is on the rounded
    brokerage + exchange + SEBI. Pass include_brokerage=False for the 2nd+ fill of one order.
    """
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")
    turnover = _d(qty) * _d(price)
    brokerage = _inr(_d(rates["brokerage_per_order_inr"])) if include_brokerage else Decimal("0.00")
    exchange = _inr(turnover * _d(rates["exchange_txn_frac"]))
    sebi = _inr(turnover * _d(rates["sebi_fee_frac"]))
    stt = _inr(turnover * _d(rates["stt_sell_premium_frac"])) if side == "SELL" else Decimal("0.00")
    stamp = _inr(turnover * _d(rates["stamp_duty_buy_frac"])) if side == "BUY" else Decimal("0.00")
    gst = _inr((brokerage + exchange + sebi) * _d(rates["gst_frac"]))
    total = brokerage + exchange + sebi + stt + stamp + gst
    return {
        "turnover": float(turnover),
        "brokerage": float(brokerage),
        "stt": float(stt),
        "exchange": float(exchange),
        "sebi": float(sebi),
        "stamp": float(stamp),
        "gst": float(gst),
        "total": float(total),
    }
