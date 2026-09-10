"""Append-only paper warehouse. No live orders. Never writes transcripts.sqlite."""

from warehouse.feasibility import FeasibilityDecision, evaluate_long_premium
from warehouse.ohlc import TIMEFRAMES, normalize_tf
from warehouse.store import Warehouse

__version__ = "0.1.0"
__all__ = [
    "Warehouse",
    "FeasibilityDecision",
    "evaluate_long_premium",
    "TIMEFRAMES",
    "normalize_tf",
]
