"""Append-only paper warehouse. No live orders. Never writes transcripts.sqlite."""

from warehouse.etl import EtlReport, attribution_chain, run_etl
from warehouse.feasibility import FeasibilityDecision, evaluate_long_premium
from warehouse.ohlc import TIMEFRAMES, normalize_tf
from warehouse.store import Warehouse

__version__ = "0.1.0"
__all__ = [
    "TIMEFRAMES",
    "EtlReport",
    "FeasibilityDecision",
    "Warehouse",
    "attribution_chain",
    "evaluate_long_premium",
    "normalize_tf",
    "run_etl",
]
