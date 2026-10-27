"""Shadow follow must cost O(new bytes) per poll, not O(whole day tape)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from shadow.runner import TapeTail, load_tape_envelopes


def _tick(i: int) -> str:
    return (
        json.dumps(
            {
                "instrument_id": "NSE_FNO:NIFTY-22350-PE",
                "ltp": 100 + i % 7,
                "exchange_ts": f"2026-10-12T{9 + i // 3600:02d}:{i // 60 % 60:02d}:{i % 60:02d}+05:30",
            }
        )
        + "\n"
    )


def _junk(i: int) -> str:
    return json.dumps({"kind": "subscription", "n": i}) + "\n"


def test_tail_reads_only_appended_complete_lines(tmp_path: Path) -> None:
    tape = tmp_path / "tape"
    tape.mkdir()
    q = tape / "depth_quotes.jsonl"
    q.write_text("".join(_tick(i) for i in range(5)) + _tick(5)[:20])  # last line still being written
    tail = TapeTail(tape)
    assert len(tail.poll()) == 5
    assert tail.poll() == []
    with q.open("a") as fh:
        fh.write(_tick(5)[20:] + _tick(6))
    got = tail.poll()
    assert [t.ltp for t in got] == [100 + 5, 100 + 6]


def test_bad_lines_counted_not_logged(tmp_path: Path, caplog) -> None:
    tape = tmp_path / "tape"
    tape.mkdir()
    (tape / "subscriptions.jsonl").write_text("".join(_junk(i) for i in range(1000)))
    tail = TapeTail(tape)
    with caplog.at_level(logging.WARNING):
        assert tail.poll() == [] and tail.poll() == []
    assert tail.bad_lines["subscriptions.jsonl"] == 1000  # counted once, not once per poll
    assert not [r for r in caplog.records if "Skipped bad line" in r.getMessage()]


def test_poll_cost_flat_as_tape_grows(tmp_path: Path) -> None:
    """Benchmark: idle/small polls stay fast on a large day; old full re-read grows linearly."""
    tape = tmp_path / "tape"
    tape.mkdir()
    q = tape / "depth_quotes.jsonl"
    q.write_text("".join(_tick(i) for i in range(60_000)))
    (tape / "raw_frames.jsonl").write_text("".join(_junk(i) for i in range(60_000)))
    tail = TapeTail(tape)
    tail.poll()
    t0 = time.perf_counter()
    for k in range(20):
        with q.open("a") as fh:
            fh.write(_tick(60_000 + k))
        assert len(tail.poll()) == 1
    per_poll = (time.perf_counter() - t0) / 20
    t1 = time.perf_counter()
    load_tape_envelopes(tape)
    full = time.perf_counter() - t1
    assert per_poll < 0.05, per_poll
    assert per_poll * 20 < full, (per_poll, full)
