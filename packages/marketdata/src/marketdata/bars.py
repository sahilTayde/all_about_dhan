"""Bar builder: ticks to closed 1m bars, stamped at bucket close."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from contracts.clock import IST
from contracts.payloads import BarClosed, Tick


@dataclass
class _OpenBar:
    """Open bar state."""

    instrument_id: str
    start: datetime
    end: datetime
    o: float | None = None
    h: float | None = None
    lo: float | None = None
    c: float | None = None
    v: int = 0
    n_ticks: int = 0
    gap_detected: bool = False
    last_tick_ts: datetime | None = None


class BarBuilder:
    """
    Build 1m bars from ticks.

    Critical correctness properties (REG-01a):
    - Bar [start, end) is closed at first tick >= end OR at CLOCK heartbeat end + finalize_delay
    - Bar.available_ts = close time (when bar was finalized)
    - Bars never revised after close
    - Late ticks (arriving after bar closed) are counted and dropped
    """

    def __init__(self, finalize_delay_s: float = 1.5, gap_threshold_s: float = 30.0):
        """
        Initialize bar builder.

        Args:
            finalize_delay_s: seconds to wait after bucket close before forcing finalization
            gap_threshold_s: seconds between ticks to flag a gap
        """
        self._finalize_delay = timedelta(seconds=finalize_delay_s)
        self._gap_threshold = timedelta(seconds=gap_threshold_s)
        self._open_bars: dict[str, _OpenBar] = {}
        self._closed_bar_ends: dict[str, datetime] = {}
        self.late_tick_count: int = 0

    def on_tick(self, tick: Tick, available_ts: datetime) -> list[BarClosed]:
        """
        Process a tick.

        Args:
            tick: incoming tick
            available_ts: when this tick became available (event time)

        Returns:
            List of finalized bars (empty if no bars closed)
        """
        if tick.exchange_ts is None:
            return []

        event_ts = self._parse_ts(tick.exchange_ts)
        instrument_id = tick.instrument_id

        # Check if this tick is late (arrives after bar already closed)
        last_closed_end = self._closed_bar_ends.get(instrument_id)
        if last_closed_end is not None and event_ts < last_closed_end:
            self.late_tick_count += 1
            return []

        # Determine bar bucket
        bucket_start = self._bucket_start(event_ts)
        bucket_end = bucket_start + timedelta(minutes=1)

        closed_bars: list[BarClosed] = []

        # Close any open bar if this tick is in a new bucket
        if instrument_id in self._open_bars:
            open_bar = self._open_bars[instrument_id]
            if event_ts >= open_bar.end:
                # This tick triggers bar close
                closed_bars.append(self._finalize_bar(open_bar, available_ts))
                del self._open_bars[instrument_id]

        # Start new bar if needed
        if instrument_id not in self._open_bars:
            self._open_bars[instrument_id] = _OpenBar(
                instrument_id=instrument_id,
                start=bucket_start,
                end=bucket_end,
            )

        # Update open bar with this tick
        bar = self._open_bars[instrument_id]
        if tick.ltp is not None:
            if bar.o is None:
                bar.o = tick.ltp
            bar.h = tick.ltp if bar.h is None else max(bar.h, tick.ltp)
            bar.lo = tick.ltp if bar.lo is None else min(bar.lo, tick.ltp)
            bar.c = tick.ltp

        if tick.volume is not None:
            bar.v += tick.volume if tick.ltq is None else tick.ltq

        bar.n_ticks += 1

        # Gap detection
        if bar.last_tick_ts is not None and (event_ts - bar.last_tick_ts) > self._gap_threshold:
            bar.gap_detected = True

        bar.last_tick_ts = event_ts

        return closed_bars

    def on_clock(self, clock_ts: datetime) -> list[BarClosed]:
        """
        Process CLOCK heartbeat to finalize stale bars.

        Args:
            clock_ts: current clock time

        Returns:
            List of finalized bars
        """
        closed_bars: list[BarClosed] = []

        # Find bars that should be finalized (end + finalize_delay <= clock_ts)
        to_close = []
        for instrument_id, bar in self._open_bars.items():
            if bar.end + self._finalize_delay <= clock_ts:
                to_close.append(instrument_id)

        # Finalize them
        for instrument_id in to_close:
            bar = self._open_bars.pop(instrument_id)
            closed_bars.append(self._finalize_bar(bar, clock_ts))

        return closed_bars

    def _finalize_bar(self, bar: _OpenBar, available_ts: datetime) -> BarClosed:
        """
        Finalize an open bar.

        Args:
            bar: open bar to finalize
            available_ts: when this bar becomes available

        Returns:
            Closed bar
        """
        # Record that we closed this bar
        self._closed_bar_ends[bar.instrument_id] = bar.end

        return BarClosed(
            instrument_id=bar.instrument_id,
            tf="1m",
            start=bar.start.isoformat(),
            end=bar.end.isoformat(),
            o=bar.o,
            h=bar.h,
            l=bar.lo,
            c=bar.c,
            v=bar.v,
            n_ticks=bar.n_ticks,
            gap=bar.gap_detected,
            late_ticks=0,  # Per-bar late ticks not tracked, global counter used
        )

    def _bucket_start(self, ts: datetime) -> datetime:
        """Compute minute bucket start for a timestamp."""
        return ts.replace(second=0, microsecond=0)

    def _parse_ts(self, ts_str: str) -> datetime:
        """Parse ISO-8601 timestamp."""
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            # Assume IST if no timezone
            dt = dt.replace(tzinfo=IST)
        return dt
