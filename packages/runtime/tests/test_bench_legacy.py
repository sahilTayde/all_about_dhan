"""Tests for bench_legacy frozen benchmark.

Manifest / frozen-file tests land with V2-17 (PR #36): they need
``scripts/ci/check_frozen_legacy.py`` and ``config/legacy_frozen.sha256``.
When #36 merges, take their complete ``test_bench_legacy.py``.
"""

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
        assert abs(summary["net_pnl_inr"] - 69364.32) < 0.01, f"Expected net +69,364.32, got {summary['net_pnl_inr']}"


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
