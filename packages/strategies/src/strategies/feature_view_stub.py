"""
FeatureView protocol stub for V2-06.

This is a TEMPORARY STUB to be replaced by packages/indicators (V2-05).
The real FeatureView will provide incremental indicators, regime labels,
and OI features. This stub defines only the minimal protocol needed for
strategy plugins to type-check.
"""

from typing import Protocol


class FeatureView(Protocol):
    """
    Stub protocol for feature access in strategies.

    The real implementation (packages/indicators, V2-05) will provide:
    - Incremental EMA, ATR, VWAP, TWAP, realized vol
    - Daily HAR forecast from pre-market inputs
    - OI change lagged strictly before the decision minute
    - Regime labels from RegimeLabeller
    - Future-lookup counter (strict mode)

    For now, strategies can type against this protocol and will get the
    real implementation when V2-05 lands.
    """

    def get(self, name: str, default: float | None = None) -> float | None:
        """
        Get a feature value by name.

        Args:
            name: Feature name (e.g. "ema_20", "atr_14", "regime_label")
            default: Default value if feature not available

        Returns:
            Feature value or default
        """
        ...

    @property
    def available_features(self) -> tuple[str, ...]:
        """Return tuple of available feature names."""
        ...
