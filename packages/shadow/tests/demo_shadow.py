"""Assert-based dry-run demo. Paper only. No network. No live orders."""

from __future__ import annotations

from pathlib import Path

from shadow.basket import KIND_APPROVED, KIND_DRY_RUN, REASON_PENDING_LAB, v2_paths
from shadow.runner import compare_day, run_once, write_cross_tape, write_fixture_tape


def main(tmp: Path) -> None:
    repo = v2_paths().repo
    cross = write_cross_tape(tmp / "cross.jsonl")
    result = run_once(
        tape=cross,
        state_dir=tmp / "state",
        mode="paper",
        day="2026-10-04",
        basket_kind=KIND_DRY_RUN,
        repo=repo,
    )
    assert result.closed_reason is None
    assert result.opens == 1 and result.flats == 1
    assert result.book.realized_pts == 15.0
    hold_tape = write_fixture_tape(tmp / "hold.jsonl")
    hold = run_once(
        tape=hold_tape,
        state_dir=tmp / "hold",
        mode="paper",
        day="2026-10-04",
        basket_kind=KIND_APPROVED,
        repo=repo,
    )
    assert hold.opens == 0
    assert hold.session_basket is not None
    assert hold.session_basket.refuse_reason() == REASON_PENDING_LAB
    body = compare_day(state_dir=tmp / "state", day="2026-10-04", legacy_path=tmp / "missing.jsonl")
    assert body["v2"]["opens"] == 1
    assert body["legacy"]["note"] == "DATA_INSUFFICIENT"
    print("demo_shadow OK", result.output_hash[:16], "pnl", result.book.realized_pts, "abstain", REASON_PENDING_LAB)


if __name__ == "__main__":
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as folder:
        main(Path(folder))
