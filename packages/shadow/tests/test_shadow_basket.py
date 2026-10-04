"""V2-27: founder-approved paper/shadow basket. Fail closed. No live orders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from shadow.basket import (
    KIND_APPROVED,
    KIND_DRY_RUN,
    REASON_EMPTY_BASKET,
    REASON_EXIT_DEFAULTS_MISSING,
    REASON_NO_BASKET,
    REASON_NO_REGISTRY,
    REASON_PENDING_LAB,
    TEST_CROSS_ID,
    load_session_basket,
    resolve_basket,
    v2_paths,
)
from shadow.journal import ShadowJournal
from shadow.runner import run_once, write_cross_tape, write_fixture_tape
from shadow.safety import ShadowClosed, ShadowSafetyError

REPO = Path(__file__).resolve().parents[3]


def _seed_v2(tmp: Path, *, registry: bool = True, exits: bool = True) -> Path:
    (tmp / "AGENT.md").write_text("seed\n", encoding="utf-8")
    baskets = tmp / "config" / "v2" / "baskets"
    baskets.mkdir(parents=True)
    (tmp / "config" / "v2" / "strategies").mkdir(parents=True, exist_ok=True)
    (tmp / "config" / "v2" / "exits").mkdir(parents=True, exist_ok=True)
    if registry:
        (tmp / "config" / "v2" / "strategies" / "registry.yaml").write_text(
            (REPO / "config" / "v2" / "strategies" / "registry.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    if exits:
        (tmp / "config" / "v2" / "exits" / "defaults.yaml").write_text(
            (REPO / "config" / "v2" / "exits" / "defaults.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return tmp


def test_approved_basket_has_no_test_cross() -> None:
    data = yaml.safe_load(
        (REPO / "config" / "v2" / "baskets" / "approved_paper_shadow.yaml").read_text(encoding="utf-8")
    )
    assert data["kind"] == "approved_paper_shadow"
    assert data["market"] == "IN_INDEX_OPT"
    ids = {row["strategy_id"] for row in data["entries"]}
    assert TEST_CROSS_ID not in ids
    stages = {row["stage"] for row in data["entries"]}
    assert stages <= {"shadow", "paper"}


def test_missing_basket_fails_closed(tmp_path: Path) -> None:
    _seed_v2(tmp_path)
    with pytest.raises(ShadowClosed, match=REASON_NO_BASKET):
        resolve_basket(session="2026-10-04", kind="auto", paths=v2_paths(tmp_path))


def test_missing_exits_fails_closed(tmp_path: Path) -> None:
    _seed_v2(tmp_path, exits=False)
    (tmp_path / "config" / "v2" / "baskets" / "approved_paper_shadow.yaml").write_text(
        (REPO / "config" / "v2" / "baskets" / "approved_paper_shadow.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    with pytest.raises(ShadowClosed, match=REASON_EXIT_DEFAULTS_MISSING):
        load_session_basket(session="2026-10-04", kind=KIND_APPROVED, paths=v2_paths(tmp_path))


def test_missing_registry_fails_closed(tmp_path: Path) -> None:
    _seed_v2(tmp_path, registry=False)
    with pytest.raises(ShadowClosed, match=REASON_NO_REGISTRY):
        load_session_basket(session="2026-10-04", kind=KIND_APPROVED, paths=v2_paths(tmp_path))


def test_empty_basket_fails_closed(tmp_path: Path) -> None:
    _seed_v2(tmp_path)
    path = tmp_path / "config" / "v2" / "baskets" / "empty.yaml"
    path.write_text(
        "kind: approved_paper_shadow\nmarket: IN_INDEX_OPT\nentries: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ShadowClosed, match=REASON_EMPTY_BASKET):
        load_session_basket(session="2026-10-04", basket_path=path, paths=v2_paths(tmp_path))


def test_live_stage_is_refused(tmp_path: Path) -> None:
    _seed_v2(tmp_path)
    path = tmp_path / "live.yaml"
    path.write_text(
        "kind: approved_paper_shadow\nmarket: IN_INDEX_OPT\nentries:\n"
        "  - strategy_id: R8-E1-COIL-SIDE\n    underlyings: [NIFTY]\n"
        "    weight: 1.0\n    max_lots: 10\n    stage: live_eligible\n",
        encoding="utf-8",
    )
    with pytest.raises(ShadowSafetyError, match="live"):
        load_session_basket(session="2026-10-04", basket_path=path, paths=v2_paths(tmp_path))


def test_test_cross_forbidden_in_approved(tmp_path: Path) -> None:
    _seed_v2(tmp_path)
    path = tmp_path / "bad.yaml"
    path.write_text(
        "kind: approved_paper_shadow\nmarket: IN_INDEX_OPT\nentries:\n"
        "  - strategy_id: TEST-CROSS\n    underlyings: [NIFTY]\n"
        "    weight: 1.0\n    max_lots: 10\n    stage: shadow\n",
        encoding="utf-8",
    )
    with pytest.raises(ShadowSafetyError, match="dry-run only"):
        load_session_basket(session="2026-10-04", basket_path=path, paths=v2_paths(tmp_path))


def test_approved_basket_pending_lab_reason() -> None:
    session = load_session_basket(session="2026-10-04", kind=KIND_APPROVED, paths=v2_paths(REPO))
    assert session.kind == KIND_APPROVED
    assert session.defaults_from.startswith("exit_defaults@")
    assert session.enabled_ids == ()
    assert session.refuse_reason() == REASON_PENDING_LAB
    assert "R8-E1-COIL-SIDE" in session.refuse_detail()


def test_dry_run_basket_enters(tmp_path: Path) -> None:
    tape = write_cross_tape(tmp_path / "ticks.jsonl")
    result = run_once(
        tape=tape,
        state_dir=tmp_path / "state",
        mode="paper",
        day="2026-10-04",
        basket_kind=KIND_DRY_RUN,
        repo=REPO,
    )
    assert result.closed_reason is None
    assert result.opens == 1
    assert result.flats == 1
    rows = list(ShadowJournal(tmp_path / "state").iter_jsonl(tmp_path / "state" / "2026-10-04" / "decisions.jsonl"))
    actions = [row["action"] for row in rows]
    assert "ENTER" in actions
    assert any(row["action"] == "HOLD" and row["reason"] == "PLUGIN_ABSTAIN" for row in rows)
    enter = next(row for row in rows if row["action"] == "ENTER")
    assert enter["strategy_id"] == TEST_CROSS_ID
    assert enter["defaults_from"].startswith("exit_defaults@")
    assert enter["orders"] == "REFUSED"
    pnl = list(ShadowJournal(tmp_path / "state").iter_jsonl(tmp_path / "state" / "2026-10-04" / "pnl.jsonl"))
    assert [row["kind"] for row in pnl] == ["SHADOW_OPEN", "SHADOW_FLAT"]
    assert "CANCEL" not in json.dumps(pnl)
    assert "COVER_LONG_UNWIND" not in json.dumps(pnl)


def test_run_without_basket_fails_closed(tmp_path: Path) -> None:
    _seed_v2(tmp_path)
    tape = write_fixture_tape(tmp_path / "ticks.jsonl")
    result = run_once(
        tape=tape,
        state_dir=tmp_path / "state",
        mode="paper",
        day="2026-10-04",
        repo=tmp_path,
    )
    assert result.closed_reason == REASON_NO_BASKET
    assert result.opens == 0
    assert result.decisions == 0
