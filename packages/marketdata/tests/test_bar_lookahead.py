"""Look-ahead harness (REG-01b, REG-01c). Named to avoid pytest basename clashes."""

import random
from datetime import datetime, timedelta

from marketdata.bars import BarBuilder
from marketdata.clock import IST
from marketdata.lookahead import lookahead_failures
from marketdata.sources import ListSource
from marketdata.types import BarClosed, SimClock, Tick, bucket_start, parse_ts


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


def _fingerprint(bar: BarClosed) -> tuple[str, str, str, float | None, float | None, float | None, float | None]:
    return (bar.instrument_id, bar.start, bar.end, bar.o, bar.h, bar.l, bar.c)


def test_random_cut_causality() -> None:
    """REG-01b: bars closed at or before the cut match the full run (mismatch fails)."""
    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    ticks = _stream(3600, start)
    all_bars = _run(ticks, start)
    rng = random.Random(37)
    for _ in range(10):
        cut = rng.randint(100, len(ticks) - 100)
        cut_bars = _run(ticks[:cut], start)
        cutoff = datetime.fromisoformat(ticks[cut - 1].exchange_ts)
        cut_closed = [_fingerprint(b) for b in cut_bars if parse_ts(b.end) <= cutoff]
        full_closed = [_fingerprint(b) for b in all_bars if parse_ts(b.end) <= cutoff]
        assert cut_closed == full_closed, f"cut={cut} cutoff={cutoff.isoformat()}"


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


class _EarlyEmitBuilder:
    """Deliberately broken: emits the current minute's bar on the first print (mid-bucket)."""

    def on_tick(self, tick: Tick, available_ts: datetime) -> list[BarClosed]:
        start = bucket_start(parse_ts(tick.exchange_ts))
        end = start + timedelta(minutes=1)
        return [
            BarClosed(
                instrument_id=tick.instrument_id,
                tf="1m",
                start=start.isoformat(),
                end=end.isoformat(),
                o=tick.ltp,
                h=tick.ltp,
                l=tick.ltp,
                c=tick.ltp,
                v=tick.ltq,
                n_ticks=1,
                available_ts=available_ts.isoformat(),
            )
        ]

    def on_clock(self, _clock_ts: datetime) -> list[BarClosed]:
        return []


def test_planted_lookahead_detection() -> None:
    """F3: harness self-test — an early emit (available_ts < end) is reported as a failure."""
    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    ticks = _stream(90, start)
    builder = _EarlyEmitBuilder()
    emissions: list[tuple[BarClosed, datetime]] = []
    for event in ListSource(ticks, SimClock(start)).events():
        new = (
            builder.on_tick(event.payload, event.available_ts)
            if event.event_type == "TICK"
            else builder.on_clock(event.available_ts)
        )
        for bar in new:
            emissions.append((bar, event.available_ts))
    failures = lookahead_failures(emissions)
    assert failures, "harness must catch a builder that emits mid-bucket (available_ts < end)"
    assert any("before end" in msg or "available_ts" in msg for msg in failures)


def test_bar_available_ts_property() -> None:
    """Property: the real builder produces zero harness failures."""
    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    ticks = _stream(1800, start)
    clock = SimClock(start)
    builder = BarBuilder()
    emissions: list[tuple[BarClosed, datetime]] = []
    for event in ListSource(ticks, clock).events():
        new = (
            builder.on_tick(event.payload, event.available_ts)
            if event.event_type == "TICK"
            else builder.on_clock(event.available_ts)
        )
        for bar in new:
            emissions.append((bar, event.available_ts))
    assert emissions
    assert lookahead_failures(emissions) == []
