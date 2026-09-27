"""Feature engine (incremental feature computation from bars)."""

from __future__ import annotations

from datetime import datetime

from contracts.payloads import BarClosed, EntryLocation

from indicators.core import ATR, EMA, VWAP, OIChange, RealizedVol
from indicators.location import LocationTracker, underlying_id
from indicators.view import FeatureValue, FeatureView


class FeatureEngine:
    """
    Incremental feature engine.

    Maintains incremental state per (instrument, timeframe) and computes features
    from closed bars only. All features are strictly causal (REG-01).
    """

    def __init__(self) -> None:
        """Initialize feature engine."""
        # State per (instrument_id, tf)
        self._ema20: dict[tuple[str, str], EMA] = {}
        self._atr14: dict[tuple[str, str], ATR] = {}
        self._vwap: dict[tuple[str, str], VWAP] = {}
        self._realized_vol: dict[tuple[str, str], RealizedVol] = {}

        # OI change tracker (instrument-level, not per-tf)
        self._oi_change = OIChange(lag_seconds=60)

        # Feature storage: (name, instrument_id, tf) -> FeatureValue
        self._features: dict[tuple[str, str, str], FeatureValue] = {}

        # Entry-location trackers keyed by underlying (closed 1m bars only)
        self._location: dict[str, LocationTracker] = {}

    def on_bar(self, bar: BarClosed, available_ts: datetime) -> None:
        """
        Process a closed bar and update features.

        Args:
            bar: closed bar
            available_ts: when this bar became available (must be >= bar.end)
        """
        instrument_id = bar.instrument_id
        tf = bar.tf
        key = (instrument_id, tf)

        # Bar end time
        bar_end = datetime.fromisoformat(bar.end)

        # Typical price for VWAP
        if bar.h is not None and bar.l is not None and bar.c is not None:
            typical_price = (bar.h + bar.l + bar.c) / 3.0
        elif bar.c is not None:
            typical_price = bar.c
        else:
            return  # No price data

        # EMA20
        if key not in self._ema20:
            self._ema20[key] = EMA(period=20)
        ema_val = self._ema20[key].update(bar.c) if bar.c is not None else None
        if ema_val is not None:
            self._features[("ema20", instrument_id, tf)] = FeatureValue(
                value=ema_val, as_of=bar_end, available_ts=available_ts
            )

        # ATR14
        if key not in self._atr14:
            self._atr14[key] = ATR(period=14)
        if bar.h is not None and bar.l is not None and bar.c is not None:
            atr_val = self._atr14[key].update(bar.h, bar.l, bar.c)
            if atr_val is not None:
                self._features[("atr", instrument_id, tf)] = FeatureValue(
                    value=atr_val, as_of=bar_end, available_ts=available_ts
                )

        # VWAP/TWAP
        if key not in self._vwap:
            self._vwap[key] = VWAP()
        vwap_val, mode = self._vwap[key].update(typical_price, bar.v)
        if vwap_val is not None:
            self._features[("vwap", instrument_id, tf)] = FeatureValue(
                value=vwap_val, as_of=bar_end, available_ts=available_ts
            )
            # Tag mode (vwap vs twap)
            self._features[("vwap_mode", instrument_id, tf)] = FeatureValue(
                value=1.0 if mode == "vwap" else 0.0, as_of=bar_end, available_ts=available_ts
            )

        # Realized volatility
        if key not in self._realized_vol:
            self._realized_vol[key] = RealizedVol(period=20)
        if bar.c is not None:
            vol_val = self._realized_vol[key].update(bar.c)
            if vol_val is not None:
                self._features[("realized_vol", instrument_id, tf)] = FeatureValue(
                    value=vol_val, as_of=bar_end, available_ts=available_ts
                )

        und = underlying_id(instrument_id)
        if und not in self._location:
            self._location[und] = LocationTracker()
        self._location[und].on_bar(bar, available_ts)

    def on_oi_update(self, instrument_id: str, oi: int, ts: datetime) -> None:
        """
        Record OI observation.

        Args:
            instrument_id: instrument ID
            oi: open interest value
            ts: timestamp of observation
        """
        self._oi_change.update(instrument_id, oi, ts)

    def get_oi_change(
        self, instrument_id: str, decision_ts: datetime, lookback_bars: int = 1
    ) -> float | None:
        """
        Get OI change lagged to strictly before decision_ts.

        Args:
            instrument_id: instrument ID
            decision_ts: decision timestamp
            lookback_bars: number of bars to look back

        Returns:
            OI change or None if insufficient data
        """
        return self._oi_change.get_lagged_change(instrument_id, decision_ts, lookback_bars)

    def entry_location(
        self, instrument_id: str, side: str, now: datetime, tf: str = "1m"
    ) -> EntryLocation | None:
        """EntryLocation at `now` from closed 1m bars with available_ts <= now."""
        del tf
        tracker = self._location.get(underlying_id(instrument_id))
        if tracker is None:
            return None
        return tracker.snapshot(now, side=side, instrument_id=instrument_id)

    def _merged_features(self, now: datetime | None) -> dict[tuple[str, str, str], FeatureValue]:
        features = dict(self._features)
        for tracker in self._location.values():
            asof = now if now is not None else tracker.last_available_ts()
            if asof is not None:
                features.update(tracker.feature_values(asof, side="CE"))
        return features

    def view(self, now: datetime | None = None, strict: bool = False) -> FeatureView:
        """
        Create a feature view.

        Args:
            now: current time (for strict mode future-lookup detection)
            strict: if True, raise on future lookups

        Returns:
            FeatureView
        """
        features = self._merged_features(now)
        if strict and now is not None:
            return FeatureView._create_strict(features, now)
        if now is not None:
            visible = {k: v for k, v in features.items() if v.available_ts <= now}
            return FeatureView(visible, strict=False)
        return FeatureView(features, strict=False)

    def reset_session(self) -> None:
        """Reset session-scoped state (e.g., VWAP)."""
        for vwap in self._vwap.values():
            vwap.reset()
        for tracker in self._location.values():
            tracker.reset()
