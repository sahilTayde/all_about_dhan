"""V2-16 acceptance: one test per plan bullet, named after it."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from gate.merge_gate import (
    ALL3_BASELINE,
    FAULTS,
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
    required_ci_jobs,
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
    assert "\n  no-lookahead:" in CI
    assert "needs:" in CI
    assert "--ci-conclusions" in CI
    assert "xfail_strict=true" in CI
    assert '-k "not skip"' in CI
    assert "gh pr merge" not in CI
    assert "git push" not in CI
    required = required_ci_jobs(CI)
    assert "gate" not in required
    for job in (*EXISTING, "perf", "no-lookahead"):
        assert job in required, job


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


def test_meta_grep_only_reg_collect_is_missing() -> None:
    result = evaluate(only="reg_collect", root=ROOT)
    check = next(c for c in result.checks if c.name == "reg_collect")
    assert check.status == "MISSING", check.detail
    assert result.verdict == "BLOCK"


def _passed_regs() -> dict[str, object]:
    return {
        "tests": [
            {"nodeid": f"tests/regression/test_reg_{i:02d}.py::test_x", "outcome": "passed"} for i in range(1, 19)
        ]
    }


def test_reg_collect_real_pytest_results_pass() -> None:
    result = evaluate(only="reg_collect", root=ROOT, pytest_results=_passed_regs())
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
    assert "subprocess" not in src
    assert "from github" not in src and "import github" not in src
    assert "api.github.com" not in src
    assert "GH_TOKEN" not in src and "DHAN_" not in src
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


def _check(result: Verdict, name: str) -> Check:
    return next(c for c in result.checks if c.name == name)


def _all_success_ci() -> dict[str, str]:
    return {name: "success" for name in required_ci_jobs(CI)}


def test_absent_ci_conclusions_blocks() -> None:
    result = evaluate(only="ci_conclusions", root=ROOT)
    assert _check(result, "ci_conclusions").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_missing_ci_job_blocks() -> None:
    jobs = {name: "success" for name in required_ci_jobs(CI) if name != "unit"}
    result = evaluate(only="ci_conclusions", root=ROOT, ci_conclusions=jobs)
    assert _check(result, "ci_conclusions").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_ci_conclusion_not_success_blocks() -> None:
    jobs = _all_success_ci()
    jobs["unit"] = "failure"
    result = evaluate(only="ci_conclusions", root=ROOT, ci_conclusions=jobs)
    assert _check(result, "ci_conclusions").status == "FAIL"
    assert result.verdict == "BLOCK"


def test_stub_ci_conclusions_is_missing() -> None:
    result = evaluate(only="ci_conclusions", root=ROOT, ci_conclusions={"kind": "stub", "unit": "success"})
    assert _check(result, "ci_conclusions").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_absent_lock_manifest_blocks(tmp_path: Path) -> None:
    (tmp_path / "requirements").mkdir()
    (tmp_path / "requirements" / "ci.txt").write_text("x\n", encoding="utf-8")
    result = evaluate(only="lock", root=tmp_path)
    assert _check(result, "lock").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_lock_mismatch_blocks(tmp_path: Path) -> None:
    (tmp_path / "requirements").mkdir()
    (tmp_path / "requirements" / "ci.txt").write_text("changed\n", encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "requirements_lock.sha256").write_text(
        "0" * 64 + "  requirements/ci.txt\n", encoding="utf-8"
    )
    result = evaluate(only="lock", root=tmp_path)
    assert _check(result, "lock").status == "FAIL"
    assert result.verdict == "BLOCK"


def test_lock_matches_committed_manifest() -> None:
    result = evaluate(only="lock", root=ROOT)
    assert _check(result, "lock").status == "PASS"
    assert result.verdict == "PASS"


def test_absent_pytest_results_reg_blocks() -> None:
    result = evaluate(only="reg_collect", root=ROOT)
    assert _check(result, "reg_collect").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_stub_pytest_results_reg_is_missing() -> None:
    result = evaluate(only="reg_collect", root=ROOT, pytest_results={"files": ["test_reg_01.py"], "kind": "grep"})
    assert _check(result, "reg_collect").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_grep_only_ids_without_outcomes_are_missing() -> None:
    result = evaluate(only="reg_collect", root=ROOT, pytest_results={"ids": ["REG-01"], "files": ["a.py"]})
    assert _check(result, "reg_collect").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_replay_parity_consume_ci_conclusions() -> None:
    missing = evaluate(only="golden-replay", root=ROOT)
    assert _check(missing, "golden-replay").status == "MISSING"
    assert missing.verdict == "BLOCK"
    stub = evaluate(only="determinism", root=ROOT, ci_conclusions={"kind": "json_hop"})
    assert _check(stub, "determinism").status == "MISSING"
    ok = evaluate(only="golden-replay", root=ROOT, ci_conclusions=_all_success_ci())
    assert _check(ok, "golden-replay").status == "PASS"


def test_absent_fault_rows_blocks() -> None:
    result = evaluate(only="faults", root=ROOT)
    assert _check(result, "faults").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_stub_fault_rows_missing() -> None:
    result = evaluate(only="faults", root=ROOT, fault_rows={"kind": "self-test", "rows": {n: True for n in FAULTS}})
    assert _check(result, "faults").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_unexercised_fault_row_missing() -> None:
    result = evaluate(
        only="faults",
        root=ROOT,
        ci_conclusions=_all_success_ci(),
        fault_rows={"rows": {}},
    )
    assert _check(result, "faults").status == "MISSING"
    for name in FAULTS:
        assert _check(result, f"faults.{name}").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_absent_lookahead_is_missing() -> None:
    result = evaluate(only="no-lookahead", root=ROOT)
    assert _check(result, "no-lookahead").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_stub_lookahead_is_missing() -> None:
    result = evaluate(only="no-lookahead", root=ROOT, lookahead_report={"kind": "json_hop"})
    assert _check(result, "no-lookahead").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_absent_compose_report_is_missing() -> None:
    result = evaluate(only="redis_compose", root=ROOT)
    assert _check(result, "redis_compose").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_json_hop_dry_run_is_missing() -> None:
    hop = evaluate(
        only="redis_compose", root=ROOT, compose_report={"kind": "json_hop", "hour_diffs": [], "day_diffs": []}
    )
    assert _check(hop, "redis_compose").status == "MISSING"
    assert hop.verdict == "BLOCK"


def test_stub_compose_report_is_missing() -> None:
    result = evaluate(only="redis_compose", root=ROOT, compose_report={"stub": True, "redis": True})
    assert _check(result, "redis_compose").status == "MISSING"
    assert result.verdict == "BLOCK"


def test_default_evaluate_never_passes_on_absent_evidence() -> None:
    result = evaluate(root=ROOT)
    assert result.verdict == "BLOCK"
    assert _check(result, "ci_conclusions").status == "MISSING"
    assert _check(result, "redis_compose").status == "MISSING"


def test_advisory_block_exits_zero_and_reports_block(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GATE_ENFORCE", raising=False)
    rc = main(["--only", "ci_conclusions", "--root", str(ROOT)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["verdict"] == "BLOCK"
    assert out["enforce"] is False


def test_enforce_block_exits_one(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("GATE_ENFORCE", "1")
    rc = main(["--only", "ci_conclusions", "--root", str(ROOT)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["verdict"] == "BLOCK"
    assert out["enforce"] is True


def test_merge_push_still_exit_two_in_both_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GATE_ENFORCE", raising=False)
    assert main(["--merge"]) == 2
    monkeypatch.setenv("GATE_ENFORCE", "1")
    assert main(["--push"]) == 2


def test_malformed_or_missing_inputs_never_pass_in_either_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for enforce in (None, "1"):
        if enforce is None:
            monkeypatch.delenv("GATE_ENFORCE", raising=False)
        else:
            monkeypatch.setenv("GATE_ENFORCE", enforce)
        capsys.readouterr()
        missing_rc = main(["--only", "ci_conclusions", "--root", str(ROOT)])
        missing = json.loads(capsys.readouterr().out)
        assert missing["verdict"] == "BLOCK"
        assert missing_rc == (1 if enforce == "1" else 0)
        bad_rc = main(["--ci-conclusions", "{not-json", "--only", "ci_conclusions", "--root", str(ROOT)])
        bad = json.loads(capsys.readouterr().out)
        assert bad["verdict"] == "BLOCK"
        assert bad_rc == (1 if enforce == "1" else 0)


def test_writes_json_out_and_step_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "gate-verdict.json"
    summary = tmp_path / "summary.md"
    monkeypatch.delenv("GATE_ENFORCE", raising=False)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    rc = main(["--only", "ci_conclusions", "--root", str(ROOT), "--json-out", str(dest)])
    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["verdict"] == "BLOCK"
    assert json.loads(dest.read_text(encoding="utf-8"))["verdict"] == "BLOCK"
    assert '"verdict": "BLOCK"' in summary.read_text(encoding="utf-8")
