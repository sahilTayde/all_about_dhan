"""V2-22 runtime signal / exec --account. Paper only. No live broker."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_runtime_signal_is_shared_and_paper_only(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "runtime", "signal", "--once", "--state-dir", str(tmp_path), "--mode", "paper"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["ok"] is True
    assert body["role"] == "signal"
    assert body["account_id"] is None
    assert body["live_broker"] is False
    assert "boss" in body["handlers"]
    assert "risk" not in body["handlers"]
    assert (tmp_path / "signal.ready").is_file()


def test_runtime_exec_isolates_founder(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "runtime",
            "exec",
            "--account",
            "founder",
            "--once",
            "--state-dir",
            str(tmp_path),
            "--mode",
            "paper",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["ok"] is True
    assert body["account_id"] == "founder"
    assert body["partition"] == "ledger:founder"
    assert "pos:founder" in body["produces"]
    assert "risk" in body["handlers"]
    assert (tmp_path / "exec-founder.ready").is_file()


def test_runtime_exec_unknown_account_fails_closed(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "runtime",
            "exec",
            "--account",
            "nope",
            "--once",
            "--state-dir",
            str(tmp_path),
            "--mode",
            "paper",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    err = json.loads(proc.stderr)
    assert err["ok"] is False and err["orders"] == "REFUSED"
    assert "UNKNOWN_ACCOUNT" in err["reason"]
