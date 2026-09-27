"""REG-09a/b: crash-at-start backs off, opens after 5 crashes / 10 min, reset-breaker restores."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from contracts.clock import IST, SimClock

from runtime.services import BREAKER_EXIT, RestartBreaker, reset_breaker, run_guarded

ROOT = Path(__file__).resolve().parents[2]
START = datetime(2026, 9, 28, 9, 20, tzinfo=IST)


def test_reg_09a_crash_at_start_backs_off_then_opens(tmp_path: Path) -> None:
    clock = SimClock(START)
    sleeps: list[float] = []

    def boom() -> None:
        raise RuntimeError("crash-at-start")

    codes: list[int] = []
    for _ in range(5):
        codes.append(run_guarded("engine", boom, state_dir=tmp_path, clock=clock, sleep=sleeps.append))
        clock.advance_by(timedelta(seconds=30))
    assert codes[:4] == [1, 1, 1, 1]
    assert codes[4] == BREAKER_EXIT
    assert sleeps == [1.0, 2.0, 4.0, 8.0]
    br = RestartBreaker(tmp_path, "engine", clock)
    assert br.is_open() is True
    assert br.crashes_in_window() >= 5
    # still open: next start does not run
    assert run_guarded("engine", boom, state_dir=tmp_path, clock=clock, sleep=sleeps.append) == BREAKER_EXIT
    rows = [json.loads(line) for line in (tmp_path / "restarts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(r["ts"].endswith("+05:30") for r in rows)
    assert any(r["event"] == "open" for r in rows)


def test_reg_09b_reset_breaker_restores(tmp_path: Path) -> None:
    clock = SimClock(START)
    br = RestartBreaker(tmp_path, "engine", clock)
    for _ in range(5):
        br.record_start()
        br.record_crash()
        clock.advance_by(timedelta(seconds=20))
    assert br.is_open() is True
    reset_breaker("engine", tmp_path, clock)
    assert br.is_open() is False
    ran = {"n": 0}

    def ok() -> None:
        ran["n"] += 1

    assert run_guarded("engine", ok, state_dir=tmp_path, clock=clock, sleep=lambda _s: None) == 0
    assert ran["n"] == 1
    proc = subprocess.run(
        [sys.executable, "-m", "runtime", "reset-breaker", "engine", "--state-dir", str(tmp_path), "--now", clock.now().isoformat()],
        cwd=ROOT,
        env={k: v for k, v in os.environ.items() if not k.startswith("DHAN_")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0 and "reset" in proc.stdout
