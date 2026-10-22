"""2026-10-22: per-index NO_DATA and stale FEED_DOWN fixes in the shadow tester (paper only)."""

from __future__ import annotations

import json
from pathlib import Path

from shadow.basket import KIND_APPROVED, load_session_basket, v2_paths
from shadow.decide import session_abstain
from shadow.journal import ShadowJournal
from shadow.runner import ShadowRun, _basket_underlyings, _finish_decisions, follow_tape, write_fixture_tape

REPO = Path(__file__).resolve().parents[3]
DAY = "2026-10-04"


def _rows(state: Path) -> list[dict]:
    path = state / DAY / "decisions.jsonl"
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.is_file() else []


def test_finish_logs_every_basket_index_not_only_nifty(tmp_path: Path) -> None:
    session = load_session_basket(session=DAY, kind=KIND_APPROVED, paths=v2_paths(REPO))
    shadow = ShadowRun(journal=ShadowJournal(tmp_path), day=DAY, mode="paper", session_basket=session)
    names = _basket_underlyings(shadow)
    shadow.apply_decision(session_abstain(session, instrument_id="NIFTY"), f"{DAY}T10:00:00+05:30")
    _finish_decisions(shadow)
    got = {r["underlying"] for r in _rows(tmp_path)}
    assert set(names) <= got
    # NIFTY already decided -> no second closing row for it
    assert sum(1 for r in _rows(tmp_path) if r["underlying"] == "NIFTY") == 1


def test_finish_adds_sensex_when_nifty_decided(tmp_path: Path) -> None:
    session = load_session_basket(session=DAY, kind=KIND_APPROVED, paths=v2_paths(REPO))
    shadow = ShadowRun(journal=ShadowJournal(tmp_path), day=DAY, mode="paper", session_basket=session)
    shadow.decided_underlyings.add("NIFTY")
    shadow.decisions = 5
    session.basket.entries[0].underlyings  # noqa: B018 - entries exist
    import shadow.runner as R
    orig = R._basket_underlyings
    R._basket_underlyings = lambda _s: ["NIFTY", "SENSEX"]
    try:
        _finish_decisions(shadow)
    finally:
        R._basket_underlyings = orig
    rows = _rows(tmp_path)
    assert [r["underlying"] for r in rows] == ["SENSEX"]
    assert rows[0]["action"] == "HOLD"


def test_feed_down_cleared_when_ticks_arrive(tmp_path: Path) -> None:
    tape = tmp_path / "ticks.jsonl"
    stop = tmp_path / "STOPPED.flag"
    polls = {"n": 0}

    def sleep(_s: float) -> None:
        polls["n"] += 1
        if polls["n"] == 2:
            write_fixture_tape(tape)  # feed comes up after two empty polls
        if polls["n"] >= 6:
            stop.write_text("1\n")

    result = follow_tape(
        tape=tape, state_dir=tmp_path / "state", stop_flag=stop, mode="paper", day=DAY,
        poll_s=0.0, sleep=sleep, repo=REPO,
    )
    assert result.envelopes > 0
    assert result.closed_reason is None
    status = json.loads((tmp_path / "state" / DAY / "status.json").read_text()) if (
        tmp_path / "state" / DAY / "status.json").is_file() else None
    if status is not None:
        assert status.get("closed_reason") is None


def test_feed_down_kept_when_no_ticks(tmp_path: Path) -> None:
    stop = tmp_path / "STOPPED.flag"
    result = follow_tape(
        tape=tmp_path / "none.jsonl", state_dir=tmp_path / "state", stop_flag=stop, mode="paper", day=DAY,
        poll_s=0.0, sleep=lambda _s: None, max_idle_polls=2, repo=REPO,
    )
    assert result.closed_reason == "FEED_DOWN"
