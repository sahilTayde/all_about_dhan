"""Tests for bench_legacy frozen benchmark."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SYNTHETIC_FIXTURE = REPO_ROOT / "packages/desk-ml/tests/fixtures/synthetic_session_nifty.json"


def test_synthetic_session_parity() -> None:
    """Frozen benchmark on synthetic NIFTY session reproduces parity fixture trades.

    Expected: 12 trades / net +69,309.10 (NIFTY only, seed 23, flag off, synthetic_session_nifty fixture).
    """
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.bench_legacy",
                "--day",
                "2026-09-10",
                "--tape",
                str(SYNTHETIC_FIXTURE),
                "--out",
                str(out_dir),
                "--deadline",
                "120",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env={**os.environ, "SHADOW_LOG": "0"},
            check=False,
        )

        assert result.returncode == 0, f"Benchmark failed:\n{result.stderr}"

        # Check summary
        summary_path = out_dir / "summary.json"
        assert summary_path.exists(), "summary.json not written"
        summary = json.loads(summary_path.read_text())

        # Frozen baseline: NIFTY 12 trades / net +69,309.10 (Dhan/NSE FA/73061 paper rates)
        assert summary["n_trades"] == 12, f"Expected 12 trades, got {summary['n_trades']}"
        assert abs(summary["net_pnl_inr"] - 69309.10) < 0.01, f"Expected net +69,309.10, got {summary['net_pnl_inr']}"

        # Check CSV exists and has the right number of rows
        csv_path = out_dir / "trades.csv"
        assert csv_path.exists(), "trades.csv not written"
        csv_lines = csv_path.read_text().splitlines()
        assert len(csv_lines) == 13, f"Expected 13 CSV lines (header + 12 trades), got {len(csv_lines)}"


def test_python_m_runtime_bench_legacy() -> None:
    """`python -m runtime bench-legacy` is the spec command and must hit the golden."""
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime",
                "bench-legacy",
                "--day",
                "2026-09-10",
                "--tape",
                str(SYNTHETIC_FIXTURE),
                "--out",
                str(out_dir),
                "--deadline",
                "120",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env={**os.environ, "SHADOW_LOG": "0"},
            check=False,
        )

        assert result.returncode == 0, f"python -m runtime bench-legacy failed:\n{result.stderr}"
        summary = json.loads((out_dir / "summary.json").read_text())
        assert summary["n_trades"] == 12, f"Expected 12 trades, got {summary['n_trades']}"
        assert abs(summary["net_pnl_inr"] - 69309.10) < 0.01, f"Expected net +69,309.10, got {summary['net_pnl_inr']}"


def test_no_writes_to_data_folder() -> None:
    """REG-11 guard: benchmark outputs never go into the checkout's data/ folder."""
    # Ask the CLI to write under data/. Do not mkdir/rmtree here: V2-01 conftest
    # REG-11a blocks in-process writes under data/, and the CLI must reject --out
    # before creating the directory (REG-11b).
    data_dir = REPO_ROOT / "data" / "test_bench_output"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "runtime",
            "bench-legacy",
            "--day",
            "2026-09-10",
            "--tape",
            str(SYNTHETIC_FIXTURE),
            "--out",
            str(data_dir),
            "--deadline",
            "60",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "SHADOW_LOG": "0"},
        check=False,
    )

    # Should fail with REG-11 error and create nothing under data/
    assert result.returncode == 1, "Expected failure when writing to data/"
    assert "REG-11" in result.stderr, f"Expected REG-11 error, got:\n{result.stderr}"
    assert not data_dir.exists(), f"CLI created {data_dir} before refusing"

    # Verify git status is clean (no writes happened)
    git_result = subprocess.run(
        ["git", "status", "--porcelain", "data/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert not git_result.stdout.strip(), f"Git detected changes in data/:\n{git_result.stdout}"


def test_deadline_enforced() -> None:
    """REG-10 guard: TimeoutError from the benchmark becomes CLI exit 2."""
    from unittest.mock import patch

    from runtime.bench_legacy import TimeoutError as BenchTimeout
    from runtime.bench_legacy import main as bench_main

    with (
        tempfile.TemporaryDirectory() as tmp,
        patch(
            "runtime.bench_legacy.run_benchmark",
            side_effect=BenchTimeout("Benchmark exceeded deadline"),
        ),
    ):
        rc = bench_main(
            [
                "--day",
                "2026-09-10",
                "--tape",
                str(SYNTHETIC_FIXTURE),
                "--out",
                tmp,
                "--deadline",
                "1",
            ]
        )
    assert rc == 2


def test_manifest_tamper_detection() -> None:
    """Manifest check fails when a frozen file is modified."""
    # Copy a frozen file and modify it
    test_file = REPO_ROOT / "packages/desk-ml/src/desk_ml/costs.py"
    backup = test_file.read_bytes()

    try:
        # Append a comment
        test_file.write_bytes(backup + b"\n# test modification\n")

        # Run check
        result = subprocess.run(
            [sys.executable, "scripts/ci/check_frozen_legacy.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        # Should fail
        assert result.returncode == 1, f"Expected failure, got code {result.returncode}"
        assert "MISMATCH" in result.stderr, f"Expected MISMATCH error, got:\n{result.stderr}"
        assert "costs.py" in result.stderr, "Expected costs.py to be flagged"
        assert "12 / +69,364.32" in result.stderr, f"Expected committed-golden baseline, got:\n{result.stderr}"
        assert "63 / -96,190.79" not in result.stderr

    finally:
        # Restore original
        test_file.write_bytes(backup)


def test_manifest_check_passes_on_clean_repo() -> None:
    """Manifest check passes when all frozen files are unchanged."""
    result = subprocess.run(
        [sys.executable, "scripts/ci/check_frozen_legacy.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"Manifest check failed:\n{result.stderr}"
    assert "passed" in result.stdout.lower(), f"Expected success message, got:\n{result.stdout}"


def test_frozen_check_failure_cites_tape_baseline() -> None:
    """Failure message cites the tape baseline when the checked input is a recorder tape."""
    test_file = REPO_ROOT / "packages/desk-ml/src/desk_ml/costs.py"
    backup = test_file.read_bytes()
    try:
        test_file.write_bytes(backup + b"\n# test modification\n")
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_frozen_legacy.py",
                "data/recon/paper_watch/DUAL-TAPE/nifty.jsonl",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "63 / -96,190.79" in result.stderr, f"Expected tape baseline, got:\n{result.stderr}"
        assert "12 / +69,364.32" not in result.stderr
    finally:
        test_file.write_bytes(backup)
