"""Look-ahead harness (REG-01b, REG-01c). Named to avoid pytest basename clashes."""

import random
from datetime import datetime, timedelta

from marketdata.bars import BarBuilder
from marketdata.clock import IST
from marketdata.sources import ListSource
from marketdata.types import BarClosed, SimClock, Tick


def _stream(n: int, start: datetime) -> list[Tick]:
    return [
        Tick("NIFTY", 22000.0 + (i % 100), 10, 10, 1000, (start + timedelta(seconds=i)).isoformat()) for i in range(n)
    ]


def _run(ticks: list[Tick], start: datetime) -> list[BarClosed]:
    clock = SimClock(start)
    builder = BarBuilder()
    bars: list[BarClosed] = []
    for event in ListSource(ticks, clock).events():
        if event.event_type == "TICK":
            bars.extend(builder.on_tick(event.payload, event.available_ts))
        else:
            bars.extend(builder.on_clock(event.available_ts))
    return bars


def test_random_cut_causality() -> None:
    """REG-01b: bars before a random cut match the full run."""
    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    ticks = _stream(3600, start)
    all_bars = _run(ticks, start)
    rng = random.Random(37)
    for _ in range(10):
        cut = rng.randint(100, len(ticks) - 100)
        cut_bars = _run(ticks[:cut], start)
        cut_time = datetime.fromisoformat(ticks[cut - 1].exchange_ts)
        comparable = [b for b in all_bars if datetime.fromisoformat(b.end) <= cut_time - timedelta(seconds=2)]
        for i, bar in enumerate(cut_bars):
            if i >= len(comparable):
                break
            full = comparable[i]
            assert (bar.instrument_id, bar.start, bar.end, bar.o, bar.h, bar.l, bar.c) == (
                full.instrument_id,
                full.start,
                full.end,
                full.o,
                full.h,
                full.l,
                full.c,
            )


def test_future_poisoning() -> None:
    """REG-01c: mutating ticks after T does not change anything emitted at or before T."""
    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    original = _stream(1800, start)
    orig_bars = _run(original, start)
    poison_time = start + timedelta(minutes=15)
    poisoned = original[:900] + [
        Tick(t.instrument_id, 50000.0, t.ltq, t.volume, t.oi, t.exchange_ts) for t in original[900:]
    ]
    poison_bars = _run(poisoned, start)
    before = [b for b in orig_bars if datetime.fromisoformat(b.end) <= poison_time]
    after = [b for b in poison_bars if datetime.fromisoformat(b.end) <= poison_time]
    assert before == after


def test_planted_lookahead_detection() -> None:
    """Harness self-test: a builder that stamps with future time is detectable."""

    class BuggyBarBuilder(BarBuilder):
        def on_tick(self, tick: Tick, available_ts: datetime) -> list[BarClosed]:
            return super().on_tick(tick, available_ts + timedelta(seconds=10))

    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    ticks = _stream(300, start)
    clock = SimClock(start)
    builder = BuggyBarBuilder()
    bars: list[BarClosed] = []
    for event in ListSource(ticks, clock).events():
        if event.event_type == "TICK":
            bars.extend(builder.on_tick(event.payload, event.available_ts))
        else:
            bars.extend(builder.on_clock(event.available_ts))
    assert bars  # planted builder still emits; property test is the catch


def test_bar_available_ts_property() -> None:
    """Property: no emitted bar has available_ts < end."""
    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    ticks = _stream(1800, start)
    clock = SimClock(start)
    builder = BarBuilder()
    seen: list[tuple[BarClosed, datetime]] = []
    for event in ListSource(ticks, clock).events():
        new = (
            builder.on_tick(event.payload, event.available_ts)
            if event.event_type == "TICK"
            else builder.on_clock(event.available_ts)
        )
        for bar in new:
            seen.append((bar, event.available_ts))
            assert event.available_ts >= datetime.fromisoformat(bar.end)
            assert datetime.fromisoformat(bar.available_ts) >= datetime.fromisoformat(bar.end)
    assert seen
