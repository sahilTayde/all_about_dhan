"""Append-only paper decision journal. No live broker. NO_PROMOTE."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from desk_ml.decision_journal import (
    DecisionJournal,
    candidate_id,
    install_engine_hooks,
    journal_enabled,
    uninstall_engine_hooks,
    journal_path,
    load_rows,
    make_row,
    plain_actor,
    record_engine_step,
    row_from_close,
    rows_from_step,
)

IST = timezone(timedelta(hours=5, minutes=30))
TS = int(datetime(2026, 1, 15, 10, 15, tzinfo=IST).timestamp())


def _step(**kw):
    base = {
        "underlying": "NIFTY",
        "ts": TS,
        "analyst_votes": [{"source": "follows", "side": "PE", "spoken": True}],
        "picker": {"action": "TICKET", "side": "PE"},
        "observer": {"action": "ALLOW"},
        "desk": {"opened_this_tick": True, "working": True},
        "index_regime": {"regime": "TREND", "iv": 12.4},
    }
    base.update(kw)
    return base


class _Pos:
    trade_id = "t-n"
    side = "PE"
    entry = 140.5
    stop = 132.0
    target = 149.0


def test_plain_actor_hides_mix() -> None:
    assert plain_actor("MIX-DEFAULT-BUY") == "Desk default"
    assert "MIX-" not in plain_actor("MIX-FORM-FOLLOWS")


def test_one_row_per_stage_per_candidate(tmp_path: Path) -> None:
    journal = DecisionJournal(tmp_path)
    row = make_row(
        ts=TS,
        underlying="NIFTY",
        candidate_id="t-n",
        stage="analyst",
        actor="MIX-FORM-FOLLOWS",
        decision="pass",
        reason="spoke",
        inputs={"day_type": "TREND", "vix": 12.4, "premium": 140.5, "sl": 132, "target": 149, "side": "PE"},
    )
    assert journal.append(row) is True
    assert journal.append(row) is False
    path = journal_path(tmp_path, "2026-01-15")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["stage"] == "analyst"
    assert loaded["actor"] == "Form-follows"
    assert "MIX-" not in json.dumps(loaded)
    assert loaded["inputs"]["day_type"] == "TREND"


def test_rows_from_open_step_writes_fill_chain() -> None:
    rows = rows_from_step(_step(), opens={("MIX-DEFAULT-BUY", "NIFTY"): _Pos()})
    stages = [r["stage"] for r in rows]
    assert stages == ["analyst", "desk", "overlay", "boss", "imm", "in_trade"]
    assert rows[-2]["decision"] == "fill"
    assert rows[-1]["stage"] == "in_trade"
    assert all("MIX-" not in json.dumps(r) for r in rows)
    assert rows[0]["candidate_id"] == "t-n"


def test_observer_veto_is_boss_skip() -> None:
    rows = rows_from_step(
        _step(
            desk={"opened_this_tick": False, "working": False},
            observer={"action": "VETO", "reason": "FOLLOW_GAP"},
        )
    )
    by_stage = {r["stage"]: r for r in rows}
    assert by_stage["boss"]["decision"] == "skip"
    assert "confirm" in by_stage["boss"]["reason"].lower() or "veto" in by_stage["boss"]["reason"].lower()
    assert "imm" not in by_stage


def test_coil_overlay_skip() -> None:
    rows = rows_from_step(
        _step(
            desk={"opened_this_tick": False},
            picker={"action": "TICKET", "side": "PE"},
            index_regime={"regime": "CHOP"},
        )
    )
    overlay = next(r for r in rows if r["stage"] == "overlay")
    assert overlay["decision"] == "skip"
    assert overlay["reason"] == "Skipped: coil market"


def test_record_engine_step_writes_jsonl(tmp_path: Path) -> None:
    class Eng:
        root = tmp_path
        last_step = _step()
        opens = {("MIX-DEFAULT-BUY", "NIFTY"): _Pos()}
        skips = []

    written = record_engine_step(Eng())
    assert written
    again = record_engine_step(Eng())
    assert again  # builders still return rows
    loaded = load_rows(tmp_path, day="2026-01-15")
    assert {r["stage"] for r in loaded} == {"analyst", "desk", "overlay", "boss", "imm", "in_trade"}
    assert candidate_id(underlying="NIFTY", side="PE", ts=TS, trade_id="t-n") == "t-n"


def test_write_false_ctx_disables_journal() -> None:
    class Off:
        ctx = type("C", (), {"write": False})()

    class On:
        ctx = type("C", (), {"write": True})()

    assert journal_enabled(Off()) is False
    assert journal_enabled(type("Bare", (), {})()) is False
    assert journal_enabled(On()) is True


def test_install_engine_hooks_is_idempotent() -> None:
    uninstall_engine_hooks()
    try:
        assert install_engine_hooks() is True
        assert install_engine_hooks() is False
    finally:
        uninstall_engine_hooks()


def test_close_row_is_exit() -> None:
    row = row_from_close(
        {
            "trade_id": "t-n",
            "underlying": "NIFTY",
            "closed_ts": TS + 300,
            "exit_reason": "TARGET",
            "exit": 148.9,
            "side": "PE",
        }
    )
    assert row is not None
    assert row["stage"] == "exit"
    assert row["decision"] == "exit"
    assert row["reason"] == "Target hit"
