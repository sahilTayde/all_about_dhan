"""Core incremental indicators (EMA, ATR, VWAP, realized vol, OI change)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EMA:
    """Exponential Moving Average (incremental)."""

    period: int
    alpha: float
    value: float | None = None

    def __init__(self, period: int):
        """
        Initialize EMA.

        Args:
            period: EMA period (e.g., 20 for EMA20)
        """
        self.period = period
        self.alpha = 2.0 / (period + 1)
        self.value = None

    def update(self, price: float) -> float:
        """
        Update with new price.

        Args:
            price: new price value

        Returns:
            Current EMA value
        """
        if self.value is None:
            self.value = price
        else:
            self.value = self.alpha * price + (1 - self.alpha) * self.value
        return self.value


@dataclass
class ATR:
    """Average True Range (incremental)."""

    period: int
    alpha: float
    value: float | None = None
    prev_close: float | None = None

    def __init__(self, period: int = 14):
        """
        Initialize ATR.

        Args:
            period: ATR period (default 14)
        """
        self.period = period
        self.alpha = 1.0 / period
        self.value = None
        self.prev_close = None

    def update(self, high: float, low: float, close: float) -> float | None:
        """
        Update with new bar OHLC.

        Args:
            high: bar high
            low: bar low
            close: bar close

        Returns:
            Current ATR value (None if warming up)
        """
        if self.prev_close is None:
            # First bar: use range
            true_range = high - low
        else:
            # TR = max(high - low, |high - prev_close|, |low - prev_close|)
            true_range = max(
                high - low,
                abs(high - self.prev_close),
                abs(low - self.prev_close),
            )

        if self.value is None:
            self.value = true_range
        else:
            self.value = self.alpha * true_range + (1 - self.alpha) * self.value

        self.prev_close = close
        return self.value


@dataclass
class VWAP:
    """Volume-Weighted Average Price (incremental, session-scoped)."""

    sum_pv: float = 0.0
    sum_v: float = 0.0
    mode: str = "vwap"  # "vwap" or "twap"
    n_bars: int = 0

    def update(self, price: float, volume: float | None = None) -> tuple[float | None, str]:
        """
        Update with new bar.

        Args:
            price: bar close or typical price
            volume: bar volume (None means no volume data, fallback to TWAP)

        Returns:
            (current value, mode) where mode is "vwap" or "twap"
        """
        if volume is None or volume == 0:
            # Fallback to TWAP
            self.n_bars += 1
            self.sum_pv += price
            self.mode = "twap"
            return (self.sum_pv / self.n_bars if self.n_bars > 0 else None, "twap")
        else:
            # VWAP
            pv = price * volume
            self.sum_pv += pv
            self.sum_v += volume
            self.mode = "vwap"
            return (self.sum_pv / self.sum_v if self.sum_v > 0 else None, "vwap")

    def reset(self) -> None:
        """Reset for new session."""
        self.sum_pv = 0.0
        self.sum_v = 0.0
        self.n_bars = 0


@dataclass
class RealizedVol:
    """Realized volatility (from bar returns, incremental)."""

    period: int
    returns: list[float]
    value: float | None = None
    prev_close: float | None = None

    def __init__(self, period: int = 20):
        """
        Initialize realized volatility.

        Args:
            period: lookback period in bars
        """
        self.period = period
        self.returns = []
        self.value = None
        self.prev_close = None

    def update(self, close: float) -> float | None:
        """
        Update with new bar close.

        Args:
            close: bar close price

        Returns:
            Current realized vol (None if warming up)
        """
        if self.prev_close is not None:
            log_return = math.log(close / self.prev_close)
            self.returns.append(log_return)

            # Keep only last N returns
            if len(self.returns) > self.period:
                self.returns.pop(0)

            # Compute std dev
            if len(self.returns) >= 2:
                mean_ret = sum(self.returns) / len(self.returns)
                variance = sum((r - mean_ret) ** 2 for r in self.returns) / (len(self.returns) - 1)
                self.value = math.sqrt(variance)

        self.prev_close = close
        return self.value


@dataclass
class OIChange:
    """
    OI change tracker with strict lag (REG-01).

    OI is lagged to the last snapshot **strictly before** the decision minute.
    """

    oi_history: dict[str, list[tuple[datetime, int]]]  # instrument_id -> [(ts, oi), ...]
    lag_seconds: int

    def __init__(self, lag_seconds: int = 60):
        """
        Initialize OI change tracker.

        Args:
            lag_seconds: minimum lag in seconds (default 60s = 1 minute)
        """
        self.oi_history = {}
        self.lag_seconds = lag_seconds

    def update(self, instrument_id: str, oi: int, ts: datetime) -> None:
        """
        Record new OI observation.

        Args:
            instrument_id: instrument ID
            oi: open interest value
            ts: timestamp of observation
        """
        if instrument_id not in self.oi_history:
            self.oi_history[instrument_id] = []

        self.oi_history[instrument_id].append((ts, oi))

        # Keep only last 100 observations per instrument (memory limit)
        if len(self.oi_history[instrument_id]) > 100:
            self.oi_history[instrument_id] = self.oi_history[instrument_id][-100:]

    def get_lagged_change(
        self, instrument_id: str, decision_ts: datetime, lookback_bars: int = 1
    ) -> float | None:
        """
        Get OI change lagged to strictly before decision_ts.

        Args:
            instrument_id: instrument ID
            decision_ts: decision timestamp
            lookback_bars: number of bars to look back for change (default 1)

        Returns:
            OI change (current - lagged) or None if insufficient data
        """
        if instrument_id not in self.oi_history:
            return None

        history = self.oi_history[instrument_id]
        if len(history) < 2:
            return None

        # Find latest OI strictly before decision_ts
        lagged_cutoff = decision_ts
        valid_entries = [(ts, oi) for ts, oi in history if ts < lagged_cutoff]

        if len(valid_entries) < lookback_bars + 1:
            return None

        # Current (lagged) and previous
        current_oi = valid_entries[-1][1]
        previous_oi = valid_entries[-(lookback_bars + 1)][1]

        return float(current_oi - previous_oi)
