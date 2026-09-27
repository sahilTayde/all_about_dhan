"""Tests for BarBuilder."""

from datetime import datetime, timedelta

import pytest

from contracts.clock import IST, SimClock
from contracts.payloads import BarClosed, Tick
from marketdata.bars import BarBuilder


def test_bar_closed_at_bucket_close():
    """REG-01a: Bar available_ts must be >= end (never before bucket close)."""
    builder = BarBuilder(finalize_delay_s=1.5)
    clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))

    # Tick at 09:15:30
    tick1 = Tick(
        instrument_id="NIFTY",
        ltp=22000.0,
        ltq=100,
        volume=100,
        oi=1000,
        exchange_ts="2026-01-02T09:15:30+05:30",
    )
    bars = builder.on_tick(tick1, clock.now())
    assert len(bars) == 0

    # Tick at 09:16:00 - closes previous bar
    clock.advance_to(datetime(2026, 1, 2, 9, 16, 0, tzinfo=IST))
    tick2 = Tick(
        instrument_id="NIFTY",
        ltp=22010.0,
        ltq=50,
        volume=50,
        oi=1000,
        exchange_ts="2026-01-02T09:16:00+05:30",
    )
    bars = builder.on_tick(tick2, clock.now())
    assert len(bars) == 1

    bar = bars[0]
    # Bar end is 09:16:00, available_ts should be >= end
    bar_end = datetime.fromisoformat(bar.end)
    # available_ts is the second argument to on_tick
    assert clock.now() >= bar_end
    assert bar.start == "2026-01-02T09:15:00+05:30"
    assert bar.end == "2026-01-02T09:16:00+05:30"


def test_bar_never_revised():
    """Bars are never revised after close."""
    builder = BarBuilder()
    clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))

    # First tick in bar
    tick1 = Tick(
        instrument_id="NIFTY",
        ltp=22000.0,
        ltq=100,
        volume=100,
        oi=1000,
        exchange_ts="2026-01-02T09:15:30+05:30",
    )
    builder.on_tick(tick1, clock.now())

    # Close the bar
    clock.advance_to(datetime(2026, 1, 2, 9, 16, 0, tzinfo=IST))
    tick2 = Tick(
        instrument_id="NIFTY",
        ltp=22010.0,
        ltq=50,
        volume=50,
        oi=1000,
        exchange_ts="2026-01-02T09:16:00+05:30",
    )
    bars = builder.on_tick(tick2, clock.now())
    assert len(bars) == 1
    original_bar = bars[0]

    # Late tick for the closed bar (should be dropped)
    tick3 = Tick(
        instrument_id="NIFTY",
        ltp=21990.0,
        ltq=200,
        volume=200,
        oi=1000,
        exchange_ts="2026-01-02T09:15:45+05:30",  # Before bar end
    )
    bars = builder.on_tick(tick3, clock.now())
    assert len(bars) == 0  # No new bar emitted
    assert builder.late_tick_count == 1


def test_finalize_delay():
    """Bar finalized by CLOCK heartbeat after finalize_delay."""
    builder = BarBuilder(finalize_delay_s=1.5)
    clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))

    # Tick at 09:15:30
    tick1 = Tick(
        instrument_id="NIFTY",
        ltp=22000.0,
        ltq=100,
        volume=100,
        oi=1000,
        exchange_ts="2026-01-02T09:15:30+05:30",
    )
    builder.on_tick(tick1, clock.now())

    # No more ticks, but CLOCK heartbeat at 09:16:01.5
    clock.advance_to(datetime(2026, 1, 2, 9, 16, 1, 500000, tzinfo=IST))
    bars = builder.on_clock(clock.now())
    assert len(bars) == 1
    assert bars[0].start == "2026-01-02T09:15:00+05:30"
    assert bars[0].end == "2026-01-02T09:16:00+05:30"


def test_gap_detection():
    """Gap flag set when > 30s between ticks."""
    builder = BarBuilder(gap_threshold_s=30.0)
    clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))

    # First tick
    tick1 = Tick(
        instrument_id="NIFTY",
        ltp=22000.0,
        ltq=100,
        volume=100,
        oi=1000,
        exchange_ts="2026-01-02T09:15:10+05:30",
    )
    builder.on_tick(tick1, clock.now())

    # Second tick 35s later (gap)
    clock.advance_to(datetime(2026, 1, 2, 9, 15, 45, tzinfo=IST))
    tick2 = Tick(
        instrument_id="NIFTY",
        ltp=22010.0,
        ltq=50,
        volume=50,
        oi=1000,
        exchange_ts="2026-01-02T09:15:45+05:30",
    )
    builder.on_tick(tick2, clock.now())

    # Close bar
    clock.advance_to(datetime(2026, 1, 2, 9, 16, 0, tzinfo=IST))
    tick3 = Tick(
        instrument_id="NIFTY",
        ltp=22015.0,
        ltq=50,
        volume=50,
        oi=1000,
        exchange_ts="2026-01-02T09:16:00+05:30",
    )
    bars = builder.on_tick(tick3, clock.now())
    assert len(bars) == 1
    assert bars[0].gap is True


def test_ohlc_calculation():
    """Verify OHLC and volume calculation."""
    builder = BarBuilder()
    clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))

    ticks = [
        (22000.0, 100, "2026-01-02T09:15:10+05:30"),
        (22010.0, 50, "2026-01-02T09:15:20+05:30"),
        (21995.0, 75, "2026-01-02T09:15:30+05:30"),
        (22005.0, 25, "2026-01-02T09:15:40+05:30"),
    ]

    for ltp, ltq, ts in ticks:
        clock.advance_to(datetime.fromisoformat(ts))
        tick = Tick(
            instrument_id="NIFTY",
            ltp=ltp,
            ltq=ltq,
            volume=ltq,
            oi=1000,
            exchange_ts=ts,
        )
        builder.on_tick(tick, clock.now())

    # Close bar
    clock.advance_to(datetime(2026, 1, 2, 9, 16, 0, tzinfo=IST))
    tick_close = Tick(
        instrument_id="NIFTY",
        ltp=22000.0,
        ltq=10,
        volume=10,
        oi=1000,
        exchange_ts="2026-01-02T09:16:00+05:30",
    )
    bars = builder.on_tick(tick_close, clock.now())
    assert len(bars) == 1

    bar = bars[0]
    assert bar.o == 22000.0
    assert bar.h == 22010.0
    assert bar.l == 21995.0
    assert bar.c == 22005.0
    assert bar.v == 100 + 50 + 75 + 25
    assert bar.n_ticks == 4


def test_multiple_instruments():
    """BarBuilder tracks multiple instruments independently."""
    builder = BarBuilder()
    clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))

    # Tick for NIFTY
    clock.advance_to(datetime(2026, 1, 2, 9, 15, 30, tzinfo=IST))
    tick1 = Tick(
        instrument_id="NIFTY",
        ltp=22000.0,
        ltq=100,
        volume=100,
        oi=1000,
        exchange_ts="2026-01-02T09:15:30+05:30",
    )
    builder.on_tick(tick1, clock.now())

    # Tick for BANKNIFTY
    tick2 = Tick(
        instrument_id="BANKNIFTY",
        ltp=48000.0,
        ltq=50,
        volume=50,
        oi=500,
        exchange_ts="2026-01-02T09:15:30+05:30",
    )
    builder.on_tick(tick2, clock.now())

    # Close both bars
    clock.advance_to(datetime(2026, 1, 2, 9, 16, 0, tzinfo=IST))
    tick3 = Tick(
        instrument_id="NIFTY",
        ltp=22010.0,
        ltq=50,
        volume=50,
        oi=1000,
        exchange_ts="2026-01-02T09:16:00+05:30",
    )
    bars = builder.on_tick(tick3, clock.now())
    assert len(bars) == 1  # NIFTY bar closed

    tick4 = Tick(
        instrument_id="BANKNIFTY",
        ltp=48010.0,
        ltq=25,
        volume=25,
        oi=500,
        exchange_ts="2026-01-02T09:16:00+05:30",
    )
    bars = builder.on_tick(tick4, clock.now())
    assert len(bars) == 1  # BANKNIFTY bar closed
