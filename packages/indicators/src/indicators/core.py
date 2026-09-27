"""Core incremental indicators (EMA, ATR, VWAP, realized vol, OI change)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from marketdata.clock import IST


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
    """Session VWAP with a TWAP fallback. Accumulators stay separate.

    Once any bar with volume > 0 is seen, later zero/None-volume bars contribute
    nothing (illiquid option prints must not mix raw price into sum_pv). Before
    the first volume bar — and all session for index instruments with no volume —
    the reported value is TWAP.
    """

    sum_pv: float = 0.0
    sum_v: float = 0.0
    sum_p: float = 0.0
    n_bars: int = 0
    seen_volume: bool = False
    mode: str = "twap"

    def update(self, price: float, volume: float | None = None) -> tuple[float | None, str]:
        """Update with a bar. Returns (value, 'vwap'|'twap')."""
        if volume is not None and volume > 0:
            self.seen_volume = True
            self.sum_pv += price * volume
            self.sum_v += volume
            self.mode = "vwap"
            return (self.sum_pv / self.sum_v, "vwap")
        if self.seen_volume:
            self.mode = "vwap"
            return (self.sum_pv / self.sum_v if self.sum_v > 0 else None, "vwap")
        self.n_bars += 1
        self.sum_p += price
        self.mode = "twap"
        return (self.sum_p / self.n_bars, "twap")

    def reset(self) -> None:
        """Reset every accumulator for a new session."""
        self.sum_pv = 0.0
        self.sum_v = 0.0
        self.sum_p = 0.0
        self.n_bars = 0
        self.seen_volume = False
        self.mode = "twap"


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
        """Update with a bar close. Non-positive prices skip the return (no domain error)."""
        if close <= 0:
            return self.value
        if self.prev_close is not None and self.prev_close > 0:
            log_return = math.log(close / self.prev_close)
            self.returns.append(log_return)
            if len(self.returns) > self.period:
                self.returns.pop(0)
            if len(self.returns) >= 2:
                mean_ret = sum(self.returns) / len(self.returns)
                variance = sum((r - mean_ret) ** 2 for r in self.returns) / (len(self.returns) - 1)
                self.value = math.sqrt(variance)
        self.prev_close = close
        return self.value


def _floor_minute_ist(ts: datetime) -> datetime:
    """Floor ``ts`` to the IST minute (naive values are treated as IST)."""
    local = ts.replace(tzinfo=IST) if ts.tzinfo is None else ts.astimezone(IST)
    return local.replace(second=0, microsecond=0)


@dataclass
class OIChange:
    """OI change lagged to the last snapshot strictly before the decision minute (REG-01)."""

    oi_history: dict[str, list[tuple[datetime, int]]]

    def __init__(self) -> None:
        self.oi_history = {}

    def update(self, instrument_id: str, oi: int, ts: datetime) -> None:
        if instrument_id not in self.oi_history:
            self.oi_history[instrument_id] = []
        self.oi_history[instrument_id].append((ts, oi))
        if len(self.oi_history[instrument_id]) > 100:
            self.oi_history[instrument_id] = self.oi_history[instrument_id][-100:]

    def get_lagged_change(
        self, instrument_id: str, decision_ts: datetime, lookback_bars: int = 1
    ) -> float | None:
        """OI change using only snapshots with ``ts < floor_minute(decision_ts)`` in IST."""
        if instrument_id not in self.oi_history:
            return None
        history = self.oi_history[instrument_id]
        cutoff = _floor_minute_ist(decision_ts)
        valid_entries = [(ts, oi) for ts, oi in history if ts < cutoff]
        if len(valid_entries) < lookback_bars + 1:
            return None
        current_oi = valid_entries[-1][1]
        previous_oi = valid_entries[-(lookback_bars + 1)][1]
        return float(current_oi - previous_oi)
