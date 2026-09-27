"""Closed-bar builder: ticks -> 1m bars; closed 1m bars -> 3m/5m.

A bar ``[start, end)`` is emitted only at bucket close (first tick with
``event_ts >= end``, or a CLOCK heartbeat at ``end + finalize_delay``).
``available_ts`` is the close time. Bars are never revised. Late ticks are
counted and dropped. Higher timeframes are stamped at ``start + tf``, never
at the last 1m print (REG-01a).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from marketdata.clock import IST, MARKET_OPEN
from marketdata.types import BarClosed, Tick, bucket_start, parse_ts


@dataclass
class _OpenBar:
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
    """Build 1m bars from ticks. One open bar per instrument."""

    def __init__(self, finalize_delay_s: float = 1.5, gap_threshold_s: float = 30.0) -> None:
        self._finalize_delay = timedelta(seconds=finalize_delay_s)
        self._gap_threshold = timedelta(seconds=gap_threshold_s)
        self._open_bars: dict[str, _OpenBar] = {}
        self._closed_bar_ends: dict[str, datetime] = {}
        self.late_tick_count: int = 0

    def on_tick(self, tick: Tick, available_ts: datetime) -> list[BarClosed]:
        if not tick.exchange_ts:
            return []

        event_ts = parse_ts(tick.exchange_ts)
        instrument_id = tick.instrument_id

        last_closed_end = self._closed_bar_ends.get(instrument_id)
        if last_closed_end is not None and event_ts < last_closed_end:
            self.late_tick_count += 1
            return []

        start = bucket_start(event_ts)
        end = start + timedelta(minutes=1)
        closed: list[BarClosed] = []

        open_bar = self._open_bars.get(instrument_id)
        if open_bar is not None and event_ts >= open_bar.end:
            closed.append(self._finalize(open_bar, available_ts))
            del self._open_bars[instrument_id]

        if instrument_id not in self._open_bars:
            self._open_bars[instrument_id] = _OpenBar(instrument_id=instrument_id, start=start, end=end)

        bar = self._open_bars[instrument_id]
        if tick.ltp is not None:
            if bar.o is None:
                bar.o = tick.ltp
            bar.h = tick.ltp if bar.h is None else max(bar.h, tick.ltp)
            bar.lo = tick.ltp if bar.lo is None else min(bar.lo, tick.ltp)
            bar.c = tick.ltp
        if tick.ltq is not None:
            bar.v += tick.ltq
        elif tick.volume is not None:
            bar.v += tick.volume
        bar.n_ticks += 1
        if bar.last_tick_ts is not None and (event_ts - bar.last_tick_ts) > self._gap_threshold:
            bar.gap_detected = True
        bar.last_tick_ts = event_ts
        return closed

    def on_clock(self, clock_ts: datetime) -> list[BarClosed]:
        to_close = [
            instrument_id
            for instrument_id, bar in self._open_bars.items()
            if bar.end + self._finalize_delay <= clock_ts
        ]
        closed: list[BarClosed] = []
        for instrument_id in to_close:
            closed.append(self._finalize(self._open_bars.pop(instrument_id), clock_ts))
        return closed

    def _finalize(self, bar: _OpenBar, available_ts: datetime) -> BarClosed:
        if available_ts < bar.end:
            raise RuntimeError(
                f"refusing to emit bar {bar.start.isoformat()}/{bar.end.isoformat()} "
                f"at available_ts={available_ts.isoformat()} (before bucket close)"
            )
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
            late_ticks=0,
            available_ts=available_ts.isoformat(),
        )


class HigherTFBuilder:
    """3m / 5m bars from *closed* 1m bars, stamped at the higher-TF bucket close.

    The legacy 3m resample stamped each bucket at its last 1m print. This builder
    waits until a 1m bar whose ``end`` equals the higher-TF close, then emits
    with ``available_ts = bucket close``.
    """

    def __init__(self, tf_minutes: int = 3) -> None:
        if tf_minutes not in (3, 5):
            raise ValueError(f"tf_minutes must be 3 or 5, got {tf_minutes}")
        self._tf_minutes = tf_minutes
        self._tf = f"{tf_minutes}m"
        self._members: dict[str, list[BarClosed]] = {}
        self._emitted: set[str] = set()

    def on_1m(self, bar: BarClosed) -> list[BarClosed]:
        if bar.tf != "1m":
            raise ValueError("HigherTFBuilder accepts only closed 1m bars")
        start = parse_ts(bar.start)
        bar_end = parse_ts(bar.end)
        bucket0 = self._align(start)
        bucket1 = bucket0 + timedelta(minutes=self._tf_minutes)
        key = f"{bar.instrument_id}|{bucket0.isoformat()}"
        if key in self._emitted:
            return []
        self._members.setdefault(key, []).append(bar)
        if bar_end < bucket1:
            return []
        members = self._members.pop(key)
        self._emitted.add(key)
        return [self._aggregate(members, bucket0, bucket1)]

    def _align(self, ts: datetime) -> datetime:
        """Align to the IST session grid that starts at 09:15."""
        local = ts.astimezone(IST)
        open_dt = local.replace(hour=MARKET_OPEN.hour, minute=MARKET_OPEN.minute, second=0, microsecond=0)
        step = timedelta(minutes=self._tf_minutes)
        if local < open_dt:
            delta = open_dt - local
            slots = (int(delta.total_seconds()) + int(step.total_seconds()) - 1) // int(step.total_seconds())
            return open_dt - slots * step
        slot = int((local - open_dt).total_seconds() // step.total_seconds())
        return open_dt + slot * step

    def _aggregate(self, members: list[BarClosed], start: datetime, end: datetime) -> BarClosed:
        opens = [m.o for m in members if m.o is not None]
        highs = [m.h for m in members if m.h is not None]
        lows = [m.l for m in members if m.l is not None]
        closes = [m.c for m in members if m.c is not None]
        volume = sum(m.v or 0 for m in members)
        n_ticks = sum(m.n_ticks for m in members)
        return BarClosed(
            instrument_id=members[0].instrument_id,
            tf=self._tf,
            start=start.isoformat(),
            end=end.isoformat(),
            o=opens[0] if opens else None,
            h=max(highs) if highs else None,
            l=min(lows) if lows else None,
            c=closes[-1] if closes else None,
            v=volume,
            n_ticks=n_ticks,
            gap=any(m.gap for m in members) or len(members) < self._tf_minutes,
            late_ticks=0,
            available_ts=end.isoformat(),
        )
