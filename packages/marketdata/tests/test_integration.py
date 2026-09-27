"""Integration tests for bar builder with sources."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from contracts.clock import IST, SimClock
from contracts.payloads import Tick
from marketdata.bars import BarBuilder
from marketdata.sources import ListSource, TapeSource


def test_replay_from_synthetic_fixture():
    """
    Replay from a small synthetic fixture shaped like data/tape/v2 depth_quotes rows.

    This tests the full pipeline: TapeSource -> BarBuilder -> closed bars.
    """
    # Create synthetic tape file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)

        # Write 10 minutes of ticks (1 per 5 seconds)
        for i in range(120):  # 10 minutes, 1 tick per 5s
            ts = base_time + timedelta(seconds=i * 5)
            tick_json = (
                f'{{"instrument_id":"NIFTY",'
                f'"ltp":{22000.0 + (i % 20)},'
                f'"ltq":10,'
                f'"volume":10,'
                f'"oi":1000,'
                f'"exchange_ts":"{ts.isoformat()}"}}\n'
            )
            f.write(tick_json)
        tape_path = Path(f.name)

    try:
        clock = SimClock(base_time)
        source = TapeSource(tape_path, clock)
        builder = BarBuilder()

        bars: list[BarClosed] = []
        for event in source.events():
            if event.event_type == "TICK":
                new_bars = builder.on_tick(event.payload, event.available_ts)
                bars.extend(new_bars)
            elif event.event_type == "CLOCK":
                new_bars = builder.on_clock(event.available_ts)
                bars.extend(new_bars)

        # Should have ~10 closed 1m bars
        assert len(bars) >= 9  # At least 9 complete bars from 10 minutes

        # Check first bar
        first_bar = bars[0]
        assert first_bar.instrument_id == "NIFTY"
        assert first_bar.tf == "1m"
        assert first_bar.start == "2026-01-02T09:15:00+05:30"
        assert first_bar.end == "2026-01-02T09:16:00+05:30"
        assert first_bar.o is not None
        assert first_bar.h is not None
        assert first_bar.l is not None
        assert first_bar.c is not None

        # All bars should have monotonic time
        for i in range(1, len(bars)):
            prev_end = datetime.fromisoformat(bars[i - 1].end)
            curr_start = datetime.fromisoformat(bars[i].start)
            assert curr_start >= prev_end

    finally:
        tape_path.unlink()


def test_fixture_day_bar_count():
    """
    A recorder fixture day produces expected bar count.

    For a session 09:15-15:30 (6h 15m = 375 minutes), we expect:
    - 375 bars for a continuous feed
    - Fewer bars if there are gaps or missing data
    """
    # Simulate a full session (9:15-15:30 IST)
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    end_time = datetime(2026, 1, 2, 15, 30, 0, tzinfo=IST)

    ticks = []
    current = base_time
    tick_count = 0

    # Generate 1 tick every 5 seconds for the entire session
    while current <= end_time:
        tick = Tick(
            instrument_id="NIFTY",
            ltp=22000.0 + (tick_count % 100),
            ltq=10,
            volume=10,
            oi=1000,
            exchange_ts=current.isoformat(),
        )
        ticks.append(tick)
        current += timedelta(seconds=5)
        tick_count += 1

    clock = SimClock(base_time)
    source = ListSource(ticks, clock)
    builder = BarBuilder()

    bars: list[BarClosed] = []
    for event in source.events():
        if event.event_type == "TICK":
            new_bars = builder.on_tick(event.payload, event.available_ts)
            bars.extend(new_bars)
        elif event.event_type == "CLOCK":
            new_bars = builder.on_clock(event.available_ts)
            bars.extend(new_bars)

    # Should have 375 bars (one per minute from 09:15 to 15:30)
    # (15:30 - 09:15 = 6h 15m = 375 minutes)
    expected_bars = 375
    assert len(bars) >= expected_bars - 2  # Allow for finalization timing


def test_gap_in_synthetic_tape():
    """A synthetic tape with a 30s hole yields gap: true."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)

    ticks = []
    # First 20 seconds: ticks every 2s
    for i in range(10):
        ts = base_time + timedelta(seconds=i * 2)
        tick = Tick(
            instrument_id="NIFTY",
            ltp=22000.0 + i,
            ltq=10,
            volume=10,
            oi=1000,
            exchange_ts=ts.isoformat(),
        )
        ticks.append(tick)

    # GAP: 30 seconds with no ticks

    # Resume at 50s
    for i in range(10):
        ts = base_time + timedelta(seconds=50 + i * 2)
        tick = Tick(
            instrument_id="NIFTY",
            ltp=22050.0 + i,
            ltq=10,
            volume=10,
            oi=1000,
            exchange_ts=ts.isoformat(),
        )
        ticks.append(tick)

    # Add tick to close the bar (after the last tick in the second group)
    ticks.append(
        Tick(
            instrument_id="NIFTY",
            ltp=22100.0,
            ltq=10,
            volume=10,
            oi=1000,
            exchange_ts=(base_time + timedelta(seconds=70)).isoformat(),
        )
    )

    clock = SimClock(base_time)
    source = ListSource(ticks, clock)
    builder = BarBuilder(gap_threshold_s=30.0)

    bars: list[BarClosed] = []
    for event in source.events():
        if event.event_type == "TICK":
            new_bars = builder.on_tick(event.payload, event.available_ts)
            bars.extend(new_bars)
        elif event.event_type == "CLOCK":
            new_bars = builder.on_clock(event.available_ts)
            bars.extend(new_bars)

    # Should have at least 1 bar with gap flag
    assert len(bars) >= 1
    assert any(b.gap for b in bars), "Expected at least one bar with gap=True"
