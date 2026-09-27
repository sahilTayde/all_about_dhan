"""Closed 1m / 3m bar builder tests (REG-01a)."""

from datetime import datetime, timedelta

from marketdata.bars import BarBuilder, HigherTFBuilder
from marketdata.clock import IST
from marketdata.types import SimClock, Tick


def test_bar_closed_at_bucket_close() -> None:
    """REG-01a: bar available_ts is at or after end, never the last print before close."""
    builder = BarBuilder(finalize_delay_s=1.5)
    clock = SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST))  # Tuesday

    builder.on_tick(
        Tick("NIFTY", 22000.0, 100, 100, 1000, "2026-01-06T09:15:30+05:30"),
        clock.now(),
    )
    assert builder.on_tick(
        Tick("NIFTY", 22000.0, 1, 1, 1000, "2026-01-06T09:15:59+05:30"),
        datetime(2026, 1, 6, 9, 15, 59, tzinfo=IST),
    ) == []

    clock.advance_to(datetime(2026, 1, 6, 9, 16, 0, tzinfo=IST))
    bars = builder.on_tick(
        Tick("NIFTY", 22010.0, 50, 50, 1000, "2026-01-06T09:16:00+05:30"),
        clock.now(),
    )
    assert len(bars) == 1
    bar = bars[0]
    assert bar.start == "2026-01-06T09:15:00+05:30"
    assert bar.end == "2026-01-06T09:16:00+05:30"
    assert datetime.fromisoformat(bar.available_ts) >= datetime.fromisoformat(bar.end)
    assert clock.now() >= datetime.fromisoformat(bar.end)


def test_bar_never_revised() -> None:
    builder = BarBuilder()
    clock = SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST))
    builder.on_tick(Tick("NIFTY", 22000.0, 100, 100, 1000, "2026-01-06T09:15:30+05:30"), clock.now())
    clock.advance_to(datetime(2026, 1, 6, 9, 16, 0, tzinfo=IST))
    bars = builder.on_tick(Tick("NIFTY", 22010.0, 50, 50, 1000, "2026-01-06T09:16:00+05:30"), clock.now())
    assert len(bars) == 1
    first = bars[0]
    late = builder.on_tick(Tick("NIFTY", 21990.0, 200, 200, 1000, "2026-01-06T09:15:45+05:30"), clock.now())
    assert late == []
    assert builder.late_tick_count == 1
    assert first.o == 22000.0
    assert first.c == 22000.0


def test_finalize_delay() -> None:
    builder = BarBuilder(finalize_delay_s=1.5)
    clock = SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST))
    builder.on_tick(Tick("NIFTY", 22000.0, 100, 100, 1000, "2026-01-06T09:15:30+05:30"), clock.now())
    clock.advance_to(datetime(2026, 1, 6, 9, 16, 1, 500000, tzinfo=IST))
    bars = builder.on_clock(clock.now())
    assert len(bars) == 1
    assert bars[0].start == "2026-01-06T09:15:00+05:30"
    assert bars[0].end == "2026-01-06T09:16:00+05:30"
    assert datetime.fromisoformat(bars[0].available_ts) >= datetime.fromisoformat(bars[0].end)


def test_gap_detection() -> None:
    builder = BarBuilder(gap_threshold_s=30.0)
    clock = SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST))
    builder.on_tick(Tick("NIFTY", 22000.0, 100, 100, 1000, "2026-01-06T09:15:10+05:30"), clock.now())
    clock.advance_to(datetime(2026, 1, 6, 9, 15, 45, tzinfo=IST))
    builder.on_tick(Tick("NIFTY", 22010.0, 50, 50, 1000, "2026-01-06T09:15:45+05:30"), clock.now())
    clock.advance_to(datetime(2026, 1, 6, 9, 16, 0, tzinfo=IST))
    bars = builder.on_tick(Tick("NIFTY", 22015.0, 50, 50, 1000, "2026-01-06T09:16:00+05:30"), clock.now())
    assert len(bars) == 1
    assert bars[0].gap is True


def test_ohlc_calculation() -> None:
    builder = BarBuilder()
    clock = SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST))
    prints = [
        (22000.0, 100, "2026-01-06T09:15:10+05:30"),
        (22010.0, 50, "2026-01-06T09:15:20+05:30"),
        (21995.0, 75, "2026-01-06T09:15:30+05:30"),
        (22005.0, 25, "2026-01-06T09:15:40+05:30"),
    ]
    for ltp, ltq, ts in prints:
        clock.advance_to(datetime.fromisoformat(ts))
        builder.on_tick(Tick("NIFTY", ltp, ltq, ltq, 1000, ts), clock.now())
    clock.advance_to(datetime(2026, 1, 6, 9, 16, 0, tzinfo=IST))
    bars = builder.on_tick(Tick("NIFTY", 22000.0, 10, 10, 1000, "2026-01-06T09:16:00+05:30"), clock.now())
    assert len(bars) == 1
    bar = bars[0]
    assert bar.o == 22000.0
    assert bar.h == 22010.0
    assert bar.l == 21995.0
    assert bar.c == 22005.0
    assert bar.v == 250
    assert bar.n_ticks == 4


def test_multiple_instruments() -> None:
    builder = BarBuilder()
    clock = SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST))
    clock.advance_to(datetime(2026, 1, 6, 9, 15, 30, tzinfo=IST))
    builder.on_tick(Tick("NIFTY", 22000.0, 100, 100, 1000, "2026-01-06T09:15:30+05:30"), clock.now())
    builder.on_tick(Tick("BANKNIFTY", 48000.0, 50, 50, 500, "2026-01-06T09:15:30+05:30"), clock.now())
    clock.advance_to(datetime(2026, 1, 6, 9, 16, 0, tzinfo=IST))
    nifty = builder.on_tick(Tick("NIFTY", 22010.0, 50, 50, 1000, "2026-01-06T09:16:00+05:30"), clock.now())
    bank = builder.on_tick(Tick("BANKNIFTY", 48010.0, 25, 25, 500, "2026-01-06T09:16:00+05:30"), clock.now())
    assert len(nifty) == 1
    assert len(bank) == 1
    assert nifty[0].instrument_id == "NIFTY"
    assert bank[0].instrument_id == "BANKNIFTY"


def test_reg01a_3m_stamped_at_bucket_close_not_last_print() -> None:
    """REG-01a: 3m bar available_ts is the 3m close, not the last 1m print."""
    one_m = BarBuilder()
    three_m = HigherTFBuilder(3)
    clock = SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST))
    # One tick per minute at :30 (last print well before each 1m close).
    emitted_3m = []
    for minute in range(4):
        ts = datetime(2026, 1, 6, 9, 15 + minute, 30, tzinfo=IST)
        clock.advance_to(ts)
        one_m.on_tick(Tick("NIFTY", 22000.0 + minute, 10, 10, 1000, ts.isoformat()), clock.now())
        close = datetime(2026, 1, 6, 9, 16 + minute, 0, tzinfo=IST)
        clock.advance_to(close)
        for bar in one_m.on_clock(close + timedelta(seconds=2)):
            emitted_3m.extend(three_m.on_1m(bar))

    assert len(emitted_3m) == 1
    bar = emitted_3m[0]
    assert bar.tf == "3m"
    assert bar.start == "2026-01-06T09:15:00+05:30"
    assert bar.end == "2026-01-06T09:18:00+05:30"
    assert bar.available_ts == bar.end
    assert bar.o == 22000.0
    assert bar.c == 22002.0
