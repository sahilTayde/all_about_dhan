"""Tests for event sources."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from contracts.clock import IST, SimClock
from contracts.payloads import Tick
from marketdata.sources import ListSource, RecorderTapeSource, TapeSource


def test_list_source_non_decreasing_available_ts():
    """Sources emit non-decreasing available_ts."""
    ticks = [
        Tick(
            instrument_id="NIFTY",
            ltp=22000.0,
            ltq=100,
            volume=100,
            oi=1000,
            exchange_ts="2026-01-02T09:15:10+05:30",
        ),
        Tick(
            instrument_id="NIFTY",
            ltp=22010.0,
            ltq=50,
            volume=50,
            oi=1000,
            exchange_ts="2026-01-02T09:15:20+05:30",
        ),
        Tick(
            instrument_id="NIFTY",
            ltp=22015.0,
            ltq=75,
            volume=75,
            oi=1000,
            exchange_ts="2026-01-02T09:15:30+05:30",
        ),
    ]

    clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))
    source = ListSource(ticks, clock)

    last_ts = None
    for event in source.events():
        if last_ts is not None:
            assert event.available_ts >= last_ts
        last_ts = event.available_ts


def test_list_source_clock_synthesis():
    """ListSource synthesizes CLOCK events every 5s."""
    ticks = [
        Tick(
            instrument_id="NIFTY",
            ltp=22000.0,
            ltq=100,
            volume=100,
            oi=1000,
            exchange_ts="2026-01-02T09:15:10+05:30",
        ),
        Tick(
            instrument_id="NIFTY",
            ltp=22010.0,
            ltq=50,
            volume=50,
            oi=1000,
            exchange_ts="2026-01-02T09:15:25+05:30",  # 15s later
        ),
    ]

    clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))
    source = ListSource(ticks, clock)

    events = list(source.events())

    # Should have: CLOCK, TICK, CLOCK, CLOCK, TICK, CLOCK...
    clock_events = [e for e in events if e.event_type == "CLOCK"]
    tick_events = [e for e in events if e.event_type == "TICK"]

    assert len(tick_events) == 2
    assert len(clock_events) >= 2  # At least 2 CLOCK events for 15s span


def test_tape_source_bad_lines_skipped():
    """REG-06a, REG-08a: bad lines are skipped, lines before and after still load."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Good line
        f.write(
            '{"instrument_id":"NIFTY","ltp":22000.0,"ltq":100,"volume":100,"oi":1000,'
            '"exchange_ts":"2026-01-02T09:15:10+05:30"}\n'
        )
        # Truncated line (bad JSON)
        f.write('{"instrument_id":"NIFTY","ltp":22010.0,"ltq":50\n')
        # Non-JSON line
        f.write("this is not json\n")
        # Wrong schema (missing required field)
        f.write('{"instrument_id":"NIFTY","ltp":22020.0}\n')
        # Good line after bad lines
        f.write(
            '{"instrument_id":"NIFTY","ltp":22030.0,"ltq":75,"volume":75,"oi":1000,'
            '"exchange_ts":"2026-01-02T09:15:30+05:30"}\n'
        )
        tape_path = Path(f.name)

    try:
        clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))
        source = TapeSource(tape_path, clock, record_errors=True)

        tick_events = [e for e in source.events() if e.event_type == "TICK"]

        # Should have 2 good ticks (lines before and after bad lines)
        assert len(tick_events) == 2
        assert tick_events[0].payload.ltp == 22000.0
        assert tick_events[1].payload.ltp == 22030.0

        # Should have recorded 3 parse errors
        assert len(source.parse_errors) == 3
    finally:
        tape_path.unlink()


def test_tape_source_gzipped():
    """TapeSource handles gzipped files."""
    import gzip

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".jsonl.gz", delete=False) as f:
        with gzip.open(f, "wt", encoding="utf-8") as gz:
            gz.write(
                '{"instrument_id":"NIFTY","ltp":22000.0,"ltq":100,"volume":100,"oi":1000,'
                '"exchange_ts":"2026-01-02T09:15:10+05:30"}\n'
            )
            gz.write(
                '{"instrument_id":"NIFTY","ltp":22010.0,"ltq":50,"volume":50,"oi":1000,'
                '"exchange_ts":"2026-01-02T09:15:20+05:30"}\n'
            )
        tape_path = Path(f.name)

    try:
        clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))
        source = TapeSource(tape_path, clock)

        tick_events = [e for e in source.events() if e.event_type == "TICK"]
        assert len(tick_events) == 2
    finally:
        tape_path.unlink()


def test_recorder_tape_source_bad_lines():
    """REG-06a, REG-08a: recorder source skips bad lines."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Good line (recorder format with 'timestamp')
        f.write(
            '{"instrument_id":"NIFTY","ltp":22000.0,"ltq":100,"volume":100,"oi":1000,'
            '"timestamp":"2026-01-02T09:15:10+05:30"}\n'
        )
        # Bad JSON
        f.write("not json\n")
        # Good line after
        f.write(
            '{"instrument_id":"NIFTY","ltp":22030.0,"ltq":75,"volume":75,"oi":1000,'
            '"timestamp":"2026-01-02T09:15:30+05:30"}\n'
        )
        recorder_path = Path(f.name)

    try:
        clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))
        source = RecorderTapeSource(recorder_path, clock, record_errors=True)

        tick_events = [e for e in source.events() if e.event_type == "TICK"]
        assert len(tick_events) == 2
        assert len(source.parse_errors) == 1
    finally:
        recorder_path.unlink()


def test_empty_file():
    """Empty file yields no events."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tape_path = Path(f.name)

    try:
        clock = SimClock(datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST))
        source = TapeSource(tape_path, clock)

        events = list(source.events())
        assert len(events) == 0
    finally:
        tape_path.unlink()
