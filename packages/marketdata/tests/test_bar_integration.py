"""Bar-builder integration tests. Named apart from any recorder integration file."""

from datetime import datetime, timedelta
from pathlib import Path

from marketdata.bars import BarBuilder
from marketdata.clock import IST
from marketdata.sources import ListSource, TapeSource
from marketdata.types import BarClosed, SimClock, Tick


def _drive(source: ListSource | TapeSource, builder: BarBuilder) -> list[BarClosed]:
    bars: list[BarClosed] = []
    for event in source.events():
        if event.event_type == "TICK":
            bars.extend(builder.on_tick(event.payload, event.available_ts))
        else:
            bars.extend(builder.on_clock(event.available_ts))
    return bars


def test_replay_from_synthetic_depth_quotes_fixture(tmp_path: Path) -> None:
    """Replay a small synthetic fixture shaped like data/tape/v2 depth_quotes rows."""
    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    tape = tmp_path / "depth_quotes.jsonl"
    lines = []
    for i in range(120):
        ts = start + timedelta(seconds=i * 5)
        iso = ts.isoformat()
        lines.append(
            "{"
            f'"event_type":"DEPTH_QUOTE","payload":{{"instrument_id":"NIFTY","ltp":{22000.0 + (i % 20)},'
            f'"bid":22000.0,"bid_qty":10,"ask":22001.0,"ask_qty":10,"oi":1000,'
            f'"levels":{{"bid":[[22000.0,10]],"ask":[[22001.0,10]]}},'
            f'"exchange_ts":"{iso}","repeat":false}},'
            f'"source":"marketdata","event_id":"t{i}","timestamp":"{iso}","v":2,'
            f'"stream":"md:depth","event_ts":"{iso}","available_ts":"{iso}",'
            '"account_id":null,"correlation_id":null,"causation_id":null}'
        )
    tape.write_text("\n".join(lines) + "\n", encoding="utf-8")

    bars = _drive(TapeSource(tape, SimClock(start)), BarBuilder())
    # 120 ticks × 5s from 09:15:00 .. 09:24:55 → buckets 09:15 .. 09:24.
    # CLOCK tail drain finalizes the last open minute. Exactly 10 closed 1m bars.
    assert len(bars) == 10
    first = bars[0]
    assert first.instrument_id == "NIFTY"
    assert first.tf == "1m"
    assert first.start == "2026-01-06T09:15:00+05:30"
    assert first.end == "2026-01-06T09:16:00+05:30"
    assert first.o is not None
    for prev, cur in zip(bars, bars[1:], strict=False):
        assert datetime.fromisoformat(cur.start) >= datetime.fromisoformat(prev.end)


def test_fixture_day_bar_count() -> None:
    """IST session 09:15-15:30 is 375 one-minute buckets [09:15, 15:30)."""
    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    end = datetime(2026, 1, 6, 15, 30, 0, tzinfo=IST)
    ticks = []
    current = start
    i = 0
    # Exclusive of 15:30:00 — that instant is the close of [15:29, 15:30), not a new bucket.
    # Inclusive 15:30:00 would open [15:30, 15:31) and yield 376 bars.
    while current < end:
        ticks.append(Tick("NIFTY", 22000.0 + (i % 100), 10, 10, 1000, current.isoformat()))
        current += timedelta(seconds=5)
        i += 1
    bars = _drive(ListSource(ticks, SimClock(start)), BarBuilder())
    assert len(bars) == 375
    assert bars[0].start == "2026-01-06T09:15:00+05:30"
    assert bars[-1].start == "2026-01-06T15:29:00+05:30"
    assert bars[-1].end == "2026-01-06T15:30:00+05:30"


def test_gap_in_synthetic_tape() -> None:
    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    ticks = [
        Tick("NIFTY", 22000.0 + i, 10, 10, 1000, (start + timedelta(seconds=i * 2)).isoformat()) for i in range(10)
    ]
    ticks.extend(
        Tick("NIFTY", 22050.0 + i, 10, 10, 1000, (start + timedelta(seconds=50 + i * 2)).isoformat()) for i in range(10)
    )
    ticks.append(Tick("NIFTY", 22100.0, 10, 10, 1000, (start + timedelta(seconds=70)).isoformat()))
    bars = _drive(ListSource(ticks, SimClock(start)), BarBuilder(gap_threshold_s=30.0))
    assert bars
    assert any(b.gap for b in bars)
