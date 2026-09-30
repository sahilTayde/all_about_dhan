"""Dhan cost model from ledger.charges / config/charges.yaml. Paper only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ledger.charges import DEFAULT_CHARGES_PATH, load_rates, order_charges

from exitlab.types import Fill


def load_cost_rates(path: Path | None = None) -> dict[str, Any]:
    return load_rates(path or DEFAULT_CHARGES_PATH, by_exchange=True)


def fill_charges(
    fill: Fill,
    rates: dict[str, Any],
    *,
    exchange: str = "NSE",
    include_brokerage: bool = True,
) -> dict[str, float]:
    raw = order_charges(
        fill.side,
        int(fill.qty),
        fill.price,
        rates,
        include_brokerage=include_brokerage,
        exchange=exchange,
    )
    return {k: float(v) for k, v in raw.items()}


def round_trip_charges(
    qty: int,
    buy_price: float,
    sell_price: float,
    rates: dict[str, Any],
    *,
    exchange: str = "NSE",
) -> float:
    buy = order_charges("BUY", qty, buy_price, rates, exchange=exchange)
    sell = order_charges("SELL", qty, sell_price, rates, exchange=exchange)
    return float(buy["total"] + sell["total"])
