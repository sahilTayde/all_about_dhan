"""V2-16 acceptance: one test per plan bullet, named after it."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from gate.merge_gate import (
    ALL3_BASELINE,
    INVARIANTS,
    NIFTY_BASELINE,
    Check,
    Verdict,
    check_invariants,
    clean_book,
    dry_run_diffs,
    evaluate,
    exit_version_ok,
    frozen_check,
    main,
    plant_violation,
)

ROOT = Path(__file__).resolve().parents[2]
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
EXISTING = (
    "hygiene",
    "unit",
    "frozen-legacy",
    "golden-replay",
    "faults",
    "lint",
    "types",
    "integration",
    "regression",
    "determinism",
    "dry-run",
    "docs",
    "image",
)


def test_invariant_checker_catches_each_planted_violation() -> None:
    assert check_invariants(clean_book()) == []
    for name in INVARIANTS:
        assert name in check_invariants(plant_violation(name, clean_book())), name


def test_dry_run_fixture_day_zero_diffs() -> None:
    assert dry_run_diffs(hour_only=True) == []
    assert dry_run_diffs(hour_only=False) == []


def test_perf_report_within_budgets() -> None:
    result = evaluate(only="perf", root=ROOT)
    perf = next(c for c in result.checks if c.name == "perf")
    assert perf.status == "PASS", perf.detail


def test_gate_wired_as_required_ci_checks() -> None:
    for job in EXISTING:
        assert f"\n  {job}:" in CI, job
    assert "\n  perf:" in CI and "\n  gate:" in CI
    assert "xfail_strict=true" in CI
    assert '-k "not skip"' in CI
    assert "gh pr merge" not in CI
    assert "git push" not in CI


def test_reg_10b_gate_jobs_registered_with_deadline() -> None:
    from runtime.jobs import JOBS

    assert JOBS["merge-gate"] > 0 and JOBS["perf"] > 0


def test_reg_13c_exit_params_without_version_bump_fails() -> None:
    before = {"version": "1.0.0", "exit_plan": {"catastrophic": {"max_loss": 30000}}}
    after = {"version": "1.0.0", "exit_plan": {"catastrophic": {"max_loss": 1}}}
    assert exit_version_ok(before, after) is False
    assert exit_version_ok(before, {**after, "version": "1.1.0"}) is True


def test_reg_15d_no_position_open_after_flat_by_ist() -> None:
    book = clean_book()
    assert "flat_after_flat_by_ist" not in check_invariants(book)
    book.open_after_flat = True
    assert "flat_after_flat_by_ist" in check_invariants(book)


def test_meta_every_reg_id_has_collected_test() -> None:
    result = evaluate(only="reg_collect", root=ROOT)
    check = next(c for c in result.checks if c.name == "reg_collect")
    assert check.status == "PASS", check.detail


def test_trace_01_every_comment_and_reg_has_row() -> None:
    result = evaluate(only="TRACE-01", root=ROOT)
    check = next(c for c in result.checks if c.name == "TRACE-01")
    assert check.status == "PASS", check.detail


def test_missing_unknown_error_block_never_pass() -> None:
    for status in ("MISSING", "UNKNOWN", "ERROR", "FAIL"):
        v = Verdict(verdict="PASS", checks=[Check("x", status, "n")])  # type: ignore[arg-type]
        blocked = any(c.status in {"FAIL", "MISSING", "UNKNOWN", "ERROR"} for c in v.checks)
        assert blocked
    assert evaluate(only="no-such-check", root=ROOT).verdict == "BLOCK"


def test_gate_never_merges_or_pushes() -> None:
    src = (ROOT / "scripts" / "gate" / "merge_gate.py").read_text(encoding="utf-8")
    assert "git push" not in src and "gh pr merge" not in src
    assert main(["--merge"]) == 2 and main(["--push"]) == 2
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gate" / "merge_gate.py"), "--merge"],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["verdict"] == "BLOCK"


def test_frozen_legacy_baselines_stay_identical() -> None:
    assert NIFTY_BASELINE == "63 / -96,190.79"
    assert ALL3_BASELINE == "140 / -27,022.54"
    check = frozen_check(ROOT)
    assert check.status == "PASS", check.detail
    assert NIFTY_BASELINE in check.detail and ALL3_BASELINE in check.detail
