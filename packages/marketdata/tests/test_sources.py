"""Event source tests, including REG-06a / REG-08a guarded JSONL parsing."""

from datetime import datetime
from pathlib import Path

from marketdata.bars import BarBuilder
from marketdata.clock import IST
from marketdata.sources import ListSource, RecorderTapeSource, SourceEvent, TapeSource
from marketdata.types import SimClock, Tick


def test_list_source_non_decreasing_available_ts() -> None:
    ticks = [
        Tick("NIFTY", 22000.0, 100, 100, 1000, "2026-01-06T09:15:10+05:30"),
        Tick("NIFTY", 22010.0, 50, 50, 1000, "2026-01-06T09:15:20+05:30"),
        Tick("NIFTY", 22015.0, 75, 75, 1000, "2026-01-06T09:15:30+05:30"),
    ]
    source = ListSource(ticks, SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)))
    last = None
    for event in source.events():
        if last is not None:
            assert event.available_ts >= last
        last = event.available_ts


def test_list_source_clock_synthesis() -> None:
    ticks = [
        Tick("NIFTY", 22000.0, 100, 100, 1000, "2026-01-06T09:15:10+05:30"),
        Tick("NIFTY", 22010.0, 50, 50, 1000, "2026-01-06T09:15:25+05:30"),
    ]
    events = list(ListSource(ticks, SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST))).events())
    assert sum(1 for e in events if e.event_type == "TICK") == 2
    assert sum(1 for e in events if e.event_type == "CLOCK") >= 2


def test_tape_source_bad_lines_skipped(tmp_path: Path) -> None:
    """REG-06a / REG-08a: truncated, non-JSON, wrong-schema mid-file; neighbors still load."""
    tape = tmp_path / "ticks.jsonl"
    tape.write_text(
        '{"instrument_id":"NIFTY","ltp":22000.0,"ltq":100,"volume":100,"oi":1000,'
        '"exchange_ts":"2026-01-06T09:15:10+05:30"}\n'
        '{"instrument_id":"NIFTY","ltp":22010.0,"ltq":50\n'
        "this is not json\n"
        '{"instrument_id":"NIFTY","ltp":22020.0}\n'
        '{"instrument_id":"NIFTY","ltp":22030.0,"ltq":75,"volume":75,"oi":1000,'
        '"exchange_ts":"2026-01-06T09:15:30+05:30"}\n',
        encoding="utf-8",
    )
    source = TapeSource(tape, SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)), record_errors=True)
    ticks = [e for e in source.events() if e.event_type == "TICK"]
    assert len(ticks) == 2
    assert ticks[0].payload.ltp == 22000.0
    assert ticks[1].payload.ltp == 22030.0
    assert len(source.parse_errors) == 3


def test_tape_source_gzipped(tmp_path: Path) -> None:
    import gzip

    tape = tmp_path / "ticks.jsonl.gz"
    with gzip.open(tape, "wt", encoding="utf-8") as handle:
        handle.write(
            '{"instrument_id":"NIFTY","ltp":22000.0,"ltq":100,"volume":100,"oi":1000,'
            '"exchange_ts":"2026-01-06T09:15:10+05:30"}\n'
            '{"instrument_id":"NIFTY","ltp":22010.0,"ltq":50,"volume":50,"oi":1000,'
            '"exchange_ts":"2026-01-06T09:15:20+05:30"}\n'
        )
    source = TapeSource(tape, SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)))
    assert sum(1 for e in source.events() if e.event_type == "TICK") == 2


def test_recorder_tape_source_bad_lines(tmp_path: Path) -> None:
    path = tmp_path / "recon.jsonl"
    path.write_text(
        '{"instrument_id":"NIFTY","ltp":22000.0,"ltq":100,"volume":100,"oi":1000,'
        '"timestamp":"2026-01-06T09:15:10+05:30"}\n'
        "not json\n"
        '{"instrument_id":"NIFTY","ltp":22030.0,"ltq":75,"volume":75,"oi":1000,'
        '"timestamp":"2026-01-06T09:15:30+05:30"}\n',
        encoding="utf-8",
    )
    source = RecorderTapeSource(path, SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)))
    ticks = [e for e in source.events() if e.event_type == "TICK"]
    assert len(ticks) == 2
    assert len(source.parse_errors) == 1


def test_list_and_tape_emit_identical_closed_bars(tmp_path: Path) -> None:
    """F2: ListSource and TapeSource drain the same CLOCK tail; closed bars match."""
    ticks = [
        Tick("NIFTY", 22000.0, 10, 10, 1000, "2026-01-06T09:15:10+05:30"),
        Tick("NIFTY", 22010.0, 10, 10, 1000, "2026-01-06T09:15:40+05:30"),
        Tick("NIFTY", 22020.0, 10, 10, 1000, "2026-01-06T09:16:10+05:30"),
        Tick("NIFTY", 22030.0, 10, 10, 1000, "2026-01-06T09:16:40+05:30"),
    ]
    tape = tmp_path / "ticks.jsonl"
    tape.write_text(
        "".join(
            f'{{"instrument_id":"NIFTY","ltp":{t.ltp},"ltq":10,"volume":10,"oi":1000,'
            f'"exchange_ts":"{t.exchange_ts}"}}\n'
            for t in ticks
        ),
        encoding="utf-8",
    )

    def closed(events: list[SourceEvent]) -> list[tuple[str, str, float | None, float | None, int]]:
        builder = BarBuilder()
        bars = []
        for event in events:
            new = (
                builder.on_tick(event.payload, event.available_ts)
                if event.event_type == "TICK"
                else builder.on_clock(event.available_ts)
            )
            bars.extend(new)
        return [(b.start, b.end, b.o, b.c, b.n_ticks) for b in bars]

    start = datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST)
    from_list = closed(list(ListSource(ticks, SimClock(start)).events()))
    from_tape = closed(list(TapeSource(tape, SimClock(start)).events()))
    assert from_list == from_tape
    assert len(from_list) == 2  # 09:15 and 09:16, last bar finalized by shared CLOCK drain


def test_empty_file(tmp_path: Path) -> None:
    tape = tmp_path / "empty.jsonl"
    tape.write_text("", encoding="utf-8")
    events = list(TapeSource(tape, SimClock(datetime(2026, 1, 6, 9, 15, 0, tzinfo=IST))).events())
    assert events == []
