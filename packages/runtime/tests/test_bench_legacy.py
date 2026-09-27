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

    Expected: 12 trades / net +69,364.32 (NIFTY only, seed 23, flag off, synthetic_session_nifty fixture).
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

        # Frozen baseline: NIFTY 12 trades / net +69,364.32 (synthetic_session_nifty golden)
        assert summary["n_trades"] == 12, f"Expected 12 trades, got {summary['n_trades']}"
        assert abs(summary["net_pnl_inr"] - 69364.32) < 0.01, f"Expected net +69,364.32, got {summary['net_pnl_inr']}"

        # Check CSV exists and has the right number of rows
        csv_path = out_dir / "trades.csv"
        assert csv_path.exists(), "trades.csv not written"
        csv_lines = csv_path.read_text().splitlines()
        assert len(csv_lines) == 13, f"Expected 13 CSV lines (header + 12 trades), got {len(csv_lines)}"


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
            "runtime.bench_legacy",
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

    # Should fail with REG-11 error
    assert result.returncode == 1, "Expected failure when writing to data/"
    assert "REG-11" in result.stderr, f"Expected REG-11 error, got:\n{result.stderr}"

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
    """REG-10 guard: benchmark times out cleanly after deadline."""
    # Create a mock tape that will cause timeout (not actually needed, just use short deadline)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "runtime.bench_legacy",
            "--day",
            "2026-09-10",
            "--tape",
            str(SYNTHETIC_FIXTURE),
            "--deadline",
            "1",  # 1 second deadline, should timeout
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "SHADOW_LOG": "0"},
        check=False,
    )

    # Should exit with code 2 (timeout)
    assert result.returncode == 2, f"Expected timeout exit code 2, got {result.returncode}"
    assert "exceeded deadline" in result.stderr.lower(), f"Expected timeout error, got:\n{result.stderr}"


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
