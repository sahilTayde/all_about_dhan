"""FeatureView protocol stub for V2-06.

TEMPORARY STUB to be replaced by `packages/indicators` (V2-05). The real
FeatureView is incremental (EMA/ATR/VWAP, lagged OI, regime labels) and
counts future lookups. This stub is only the surface strategies type-check
against. Signature matches the V2-06b `strikes.FeatureView` protocol.
"""

from typing import Protocol


class FeatureView(Protocol):
    """Read-only feature access. Implementations must not yield future values."""

    def get(self, name: str, instrument: str = "", tf: str = "") -> object | None:
        """Return a feature available at or before the current decision time."""
        ...
