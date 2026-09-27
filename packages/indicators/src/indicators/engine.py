"""Feature engine (incremental feature computation from bars)."""

from __future__ import annotations

from datetime import datetime

from marketdata.types import BarClosed, parse_ts

from indicators.core import ATR, EMA, VWAP, OIChange, RealizedVol, _as_ist
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
        self._oi_change = OIChange()

        # Feature storage: (name, instrument_id, tf) -> FeatureValue
        self._features: dict[tuple[str, str, str], FeatureValue] = {}

    def on_bar(self, bar: BarClosed, available_ts: datetime | None = None) -> None:
        """Process a closed bar and update features.

        ``available_ts`` defaults to ``bar.available_ts`` (V2-03 stamp). A feature
        is never written from a bar whose end is after that stamp.
        """
        if available_ts is None:
            if not bar.available_ts:
                raise ValueError("closed bar missing available_ts")
            available_ts = parse_ts(bar.available_ts)
        instrument_id = bar.instrument_id
        tf = bar.tf
        key = (instrument_id, tf)

        bar_end = parse_ts(bar.end)
        if available_ts < bar_end:
            raise ValueError(
                f"refusing bar {bar.start}/{bar.end} at available_ts={available_ts.isoformat()}"
            )

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
        """OI change using snapshots with ``ts < floor_minute(decision_ts)`` in IST.

        ``decision_ts`` must be timezone-aware. Naive timestamps are rejected at
        ingest (``on_oi_update``); stored rows never raise at query time.
        """
        return self._oi_change.get_lagged_change(instrument_id, decision_ts, lookback_bars)

    @property
    def vwap_rejected_bars(self) -> int:
        """Bars rejected by every session VWAP (non-finite price/volume or negative volume)."""
        return sum(vwap.vwap_rejected_bars for vwap in self._vwap.values())

    def view(self, now: datetime, *, strict: bool = False) -> FeatureView:
        """Read-only feature view as of ``now``. ``now`` is required and must be tz-aware."""
        if now is None:
            raise ValueError("FeatureEngine.view requires now (unfiltered view is forbidden)")
        now = _as_ist(now, what="view now")
        if strict:
            return FeatureView._create_strict(self._features, now)
        visible_features = {k: v for k, v in self._features.items() if v.available_ts <= now}
        return FeatureView(visible_features, strict=False)

    def reset_session(self) -> None:
        """Reset session-scoped VWAP state and drop published vwap / vwap_mode values."""
        for vwap in self._vwap.values():
            vwap.reset()
        self._features = {
            key: value
            for key, value in self._features.items()
            if key[0] not in {"vwap", "vwap_mode"}
        }
