"""Feature view with future-lookup guard (REG-01d)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class LookAheadError(Exception):
    """Raised when a feature value from the future is accessed in strict mode."""

    pass


@dataclass(frozen=True)
class FeatureValue:
    """Feature value with provenance."""

    value: float
    as_of: datetime  # When the feature was computed
    available_ts: datetime  # When this value became knowable

    def __repr__(self) -> str:
        return (
            f"FeatureValue({self.value}, "
            f"as_of={self.as_of.isoformat()}, "
            f"available={self.available_ts.isoformat()})"
        )


class FeatureView:
    """
    Feature view for strategies.

    Provides read-only access to features with optional future-lookup detection.
    """

    def __init__(self, features: dict[tuple[str, str, str], FeatureValue], strict: bool = False):
        """
        Initialize feature view.

        Args:
            features: map of (name, instrument_id, tf) -> FeatureValue
            strict: if True, raise LookAheadError on future access
        """
        self._features = features
        self._strict = strict
        self._now: datetime | None = None
        self._lookup_count = 0
        self._future_lookup_count = 0

    @classmethod
    def _create_strict(
        cls, features: dict[tuple[str, str, str], FeatureValue], now: datetime
    ) -> FeatureView:
        """Create a strict view with a fixed 'now' timestamp."""
        view = cls(features, strict=True)
        view._now = now
        return view

    def get(
        self,
        name: str,
        instrument_id: str,
        tf: str = "1m",
        now: datetime | None = None,
    ) -> FeatureValue | None:
        """
        Get feature value.

        Args:
            name: feature name (e.g., "ema20", "atr", "vwap")
            instrument_id: instrument ID
            tf: timeframe (default "1m")
            now: current time (optional override for strict checking)

        Returns:
            FeatureValue or None if not available

        Raises:
            LookAheadError: if strict=True and feature is from the future
        """
        key = (name, instrument_id, tf)
        value = self._features.get(key)

        if value is None:
            return None

        self._lookup_count += 1

        # In strict mode, check if feature is from the future
        if self._strict:
            check_time = now if now is not None else self._now
            if check_time is not None and value.available_ts > check_time:
                self._future_lookup_count += 1
                avail_iso = value.available_ts.isoformat()
                now_iso = check_time.isoformat()
                raise LookAheadError(
                    f"Feature {name} for {instrument_id} at {tf} "
                    f"has available_ts={avail_iso} which is after now={now_iso}"
                )

        return value

    @property
    def lookup_count(self) -> int:
        """Total number of feature lookups."""
        return self._lookup_count

    @property
    def future_lookup_count(self) -> int:
        """Number of future lookups detected (in strict mode)."""
        return self._future_lookup_count
