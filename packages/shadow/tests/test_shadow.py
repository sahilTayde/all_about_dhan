"""V2 shadow launcher: paper-only, fail-closed, isolated from the legacy book."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from shadow.journal import SCHEMA, ShadowJournal
from shadow.runner import (
    compare_day,
    follow_tape,
    load_tape_envelopes,
    run_once,
    write_fixture_tape,
)
from shadow.safety import (
    ShadowSafetyError,
    assert_isolated_state,
    assert_paper_only,
    is_forbidden_write,
    refuse_broker_name,
)

REPO = Path(__file__).resolve().parents[3]


def test_live_modes_are_refused() -> None:
    for mode in ("live", "limited_live", "dhan", "LIVE"):
        with pytest.raises(ShadowSafetyError, match="live"):
            assert_paper_only(mode)
    assert assert_paper_only("paper") == "paper"
    assert assert_paper_only("shadow") == "shadow"
    assert assert_paper_only("replay") == "replay"


def test_live_broker_name_is_refused() -> None:
    with pytest.raises(ShadowSafetyError):
        refuse_broker_name("dhan")
    with pytest.raises(ShadowSafetyError):
        refuse_broker_name("live")


def test_forbidden_write_paths(tmp_path: Path) -> None:
    repo_data = tmp_path / "data"
    assert is_forbidden_write(repo_data / "recon" / "book.sqlite") is True
    assert is_forbidden_write(repo_data / "ledger" / "ledger.sqlite") is True
    assert is_forbidden_write(repo_data / "shadow" / "2026-10-04.jsonl") is True
    assert is_forbidden_write(repo_data / "shadow" / "v2" / "2026-10-04" / "decisions.jsonl") is False
    assert is_forbidden_write(tmp_path / "scratch" / "decisions.jsonl") is False
    with pytest.raises(ShadowSafetyError, match="live paper book"):
        assert_isolated_state(repo_data / "recon" / "paper")
    with pytest.raises(ShadowSafetyError, match=r"live paper book|data/shadow/v2"):
        assert_isolated_state(repo_data / "shadow")


def test_missing_tape_fails_closed(tmp_path: Path) -> None:
    missing = tmp_path / "no-tape"
    result = run_once(tape=missing, state_dir=tmp_path / "shadow-v2", mode="paper", day="2026-10-04")
    assert result.closed_reason == "FEED_DOWN"
    assert result.decisions == 0
    assert result.opens == 0
    status = json.loads((tmp_path / "shadow-v2" / "2026-10-04" / "status.json").read_text(encoding="utf-8"))
    assert status["closed_reason"] == "FEED_DOWN"
    assert status["orders"] == "REFUSED"


def test_fixture_tape_hold_only(tmp_path: Path) -> None:
    tape = write_fixture_tape(tmp_path / "ticks.jsonl")
    result = run_once(tape=tape, state_dir=tmp_path / "state", mode="paper", day="2026-10-04")
    assert result.closed_reason is None
    assert result.envelopes == 3
    assert result.decisions == 3
    assert result.holds == 3
    assert result.opens == 0
    rows = list(ShadowJournal(tmp_path / "state").iter_jsonl(tmp_path / "state" / "2026-10-04" / "decisions.jsonl"))
    assert all(row["action"] == "HOLD" for row in rows)
    assert all(row["account_id"] == "v2-shadow" for row in rows)
    assert all(row["schema"] == SCHEMA for row in rows)


def test_demo_fills_isolated_pnl(tmp_path: Path) -> None:
    tape = write_fixture_tape(tmp_path / "ticks.jsonl")
    result = run_once(
        tape=tape,
        state_dir=tmp_path / "state",
        mode="paper",
        day="2026-10-04",
        demo_fills=True,
    )
    assert result.opens == 1
    assert result.flats == 1
    assert result.book.realized_pts == 25.0
    pnl = list(ShadowJournal(tmp_path / "state").iter_jsonl(tmp_path / "state" / "2026-10-04" / "pnl.jsonl"))
    kinds = [row["kind"] for row in pnl]
    assert kinds == ["SHADOW_OPEN", "SHADOW_FLAT"]
    assert "CANCEL" not in kinds
    assert "COVER_LONG_UNWIND" not in kinds
    assert pnl[-1]["realized_pts"] == 25.0


def test_same_tape_same_hash(tmp_path: Path) -> None:
    tape = write_fixture_tape(tmp_path / "ticks.jsonl")
    a = run_once(tape=tape, state_dir=tmp_path / "a", mode="replay", day="2026-10-04")
    b = run_once(tape=tape, state_dir=tmp_path / "b", mode="replay", day="2026-10-04")
    assert a.output_hash
    assert a.output_hash == b.output_hash


def test_follow_then_stop(tmp_path: Path) -> None:
    tape = write_fixture_tape(tmp_path / "ticks.jsonl")
    stop = tmp_path / "STOPPED.flag"
    result = follow_tape(
        tape=tape,
        state_dir=tmp_path / "state",
        stop_flag=stop,
        mode="paper",
        day="2026-10-04",
        poll_s=0.0,
        sleep=lambda _s: stop.write_text("1\n", encoding="utf-8"),
        max_idle_polls=3,
    )
    assert result.decisions == 3
    assert result.opens == 0


def test_compare_read_only_legacy(tmp_path: Path) -> None:
    tape = write_fixture_tape(tmp_path / "ticks.jsonl")
    run_once(tape=tape, state_dir=tmp_path / "state", mode="paper", day="2026-10-04")
    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text('{"schema":"shadow-v1","index":"NIFTY"}\n', encoding="utf-8")
    body = compare_day(state_dir=tmp_path / "state", day="2026-10-04", legacy_path=legacy)
    assert body["v2"]["decisions"] == 3
    assert body["legacy"]["rows"] == 1
    assert body["orders"] == "REFUSED"
    assert body["promote"] is False


def test_cli_refuses_live_mode() -> None:
    from shadow.__main__ import main

    assert main(["run", "--mode", "live"]) == 2


def test_cli_dry_run(tmp_path: Path) -> None:
    from shadow.__main__ import main

    rc = main(["dry-run", "--state-dir", str(tmp_path), "--day", "2026-10-04", "--mode", "paper"])
    assert rc == 0
    assert (tmp_path / "2026-10-04" / "pnl.jsonl").is_file()


def test_cli_demo_fills_refused_on_run(tmp_path: Path) -> None:
    from shadow.__main__ import main

    rc = main(["run", "--state-dir", str(tmp_path), "--tape", str(tmp_path), "--demo-fills"])
    assert rc == 2


def test_sources_never_import_live_or_legacy_engine() -> None:
    root = REPO / "packages" / "shadow" / "src"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "DhanBroker(" not in text, path
        assert "from brokers.dhan" not in text, path
        assert "import brokers.dhan" not in text, path
        assert "from dhan_client.execution" not in text, path
        assert "import dhan_client.execution" not in text, path
        assert "ExecutionClient(" not in text, path
        assert "from desk_ml.paper_scalp" not in text, path
        assert "from desk_ml.picker" not in text, path
        assert "from desk.paper" not in text, path
        assert "from oms.router" not in text, path
        assert "COVER_LONG_UNWIND" not in text, path


def test_importing_shadow_does_not_load_live_modules() -> None:
    import shadow  # noqa: F401

    assert "brokers.dhan" not in sys.modules
    assert "desk.paper" not in sys.modules
    assert "oms.router" not in sys.modules
    assert "desk_ml.paper_scalp" not in sys.modules


def test_demo_script(tmp_path: Path) -> None:
    from demo_shadow import main as demo_main

    demo_main(tmp_path)


def test_load_tape_skips_bad_lines(tmp_path: Path) -> None:
    tape = tmp_path / "ticks.jsonl"
    tape.write_text(
        '{"instrument_id":"NIFTY","ltp":1,"ltq":1,"volume":1,"oi":1,'
        '"exchange_ts":"2026-10-04T10:00:00+05:30"}\n'
        "not-json\n"
        '{"instrument_id":"NIFTY","ltp":2,"ltq":1,"volume":1,"oi":1,'
        '"exchange_ts":"2026-10-04T10:00:01+05:30"}\n',
        encoding="utf-8",
    )
    envelopes = load_tape_envelopes(tape)
    assert len(envelopes) == 2
