"""Assert-based dry-run demo. Paper only. No network. No live orders."""

from __future__ import annotations

from pathlib import Path

from shadow.runner import compare_day, run_once, write_fixture_tape


def main(tmp: Path) -> None:
    tape = write_fixture_tape(tmp / "ticks.jsonl")
    result = run_once(tape=tape, state_dir=tmp / "state", mode="paper", day="2026-10-04", demo_fills=True)
    assert result.closed_reason is None
    assert result.opens == 1 and result.flats == 1
    assert result.book.realized_pts == 25.0
    hold = run_once(tape=tape, state_dir=tmp / "hold", mode="paper", day="2026-10-04")
    assert hold.holds == 3 and hold.opens == 0
    body = compare_day(state_dir=tmp / "state", day="2026-10-04", legacy_path=tmp / "missing.jsonl")
    assert body["v2"]["closed_pnl_pts"] == 25.0
    assert body["legacy"]["note"] == "DATA_INSUFFICIENT"
    print("demo_shadow OK", result.output_hash[:16], "pnl", result.book.realized_pts)


if __name__ == "__main__":
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as folder:
        main(Path(folder))
