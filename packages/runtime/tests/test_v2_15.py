"""V2-15 acceptance: compose replay, deploy guard/rollback, backup hash, health CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from contracts.clock import IST, SimClock

from runtime.jobs import JOBS, JobTimeout, run_with_deadline
from runtime.services import (
    backup_state,
    deploy,
    output_hash,
    restore_state,
    run_health,
    wait_ready,
    write_engine_status,
)

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "deploy" / "docker" / "compose.yaml"
DEPLOY_SH = ROOT / "deploy" / "scripts" / "deploy.sh"
TEN = datetime(2026, 9, 28, 10, 0, tzinfo=IST)
PRE = datetime(2026, 9, 28, 8, 0, tzinfo=IST)


def test_runtime_help_lists_bench_legacy_and_engine() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "runtime", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "bench-legacy" in proc.stdout and "engine" in proc.stdout
    assert "reset-breaker" in proc.stdout and "job" in proc.stdout


def test_engine_replay_writes_ready_no_creds(tmp_path: Path) -> None:
    clock = SimClock(PRE)
    status = write_engine_status(tmp_path, clock)
    body = json.loads((tmp_path / "engine_status.json").read_text(encoding="utf-8"))
    assert status.status == "READY" and body["status"] == "READY" and body["recon_ok"] is True
    assert body["ts"].endswith("+05:30")
    assert wait_ready(tmp_path, timeout_s=1.0)
    rc = subprocess.run(
        [
            sys.executable,
            "-m",
            "runtime",
            "engine",
            "--once",
            "--state-dir",
            str(tmp_path),
            "--now",
            PRE.isoformat(),
        ],
        check=False,
        cwd=ROOT,
        env={k: v for k, v in os.environ.items() if not k.startswith("DHAN_")},
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0


def test_compose_replay_profile_has_no_credentials() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert "--mode replay" in text or '"replay"' in text
    assert 'profiles: ["live-orders"]' not in text
    assert "DHAN_" not in text and "dhan_access_token" not in text
    assert "\nsecrets:" not in text
    assert 'command: ["timeout", "1800", "python", "-m", "runtime", "job", "etl"]' in text


def test_health_cli_reads_breaker_not_v2_14(tmp_path: Path) -> None:
    write_engine_status(tmp_path, SimClock(PRE))
    snap = run_health(tmp_path, SimClock(PRE), once=True)
    assert snap["engine_status"] == "READY" and snap["breaker_open"] is False
    assert snap["ts"].endswith("+05:30")
    rc = subprocess.run(
        [sys.executable, "-m", "runtime", "health", "--once", "--state-dir", str(tmp_path)],
        check=False,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0 and '"engine_status": "READY"' in rc.stdout


def test_deploy_refuses_at_1000_ist(tmp_path: Path) -> None:
    result = deploy("abc1234", state_dir=tmp_path, clock=SimClock(TEN))
    assert result["ok"] is False and result["reason"] == "MARKET_HOURS"
    assert result["ts"].endswith("+05:30")
    env = {**os.environ, "AAD_STATE_DIR": str(tmp_path), "AAD_NOW": TEN.isoformat()}
    proc = subprocess.run(
        ["bash", str(DEPLOY_SH), "abc1234"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1 and "MARKET_HOURS" in proc.stdout


def test_deploy_rolls_back_when_ready_never_arrives(tmp_path: Path) -> None:
    (tmp_path / "deployed_sha").write_text("oldsha\n", encoding="utf-8")
    (tmp_path / "marker").write_text("keep\n", encoding="utf-8")
    result = deploy(
        "newsha",
        state_dir=tmp_path,
        clock=SimClock(PRE),
        ready_timeout_s=0.2,
        start_engine=lambda: None,
    )
    assert (
        result["ok"] is False
        and result["reason"] == "READY_TIMEOUT"
        and result["rolled_back"] is True
    )
    assert (tmp_path / "deployed_sha").read_text(encoding="utf-8").strip() == "oldsha"
    assert (tmp_path / "marker").read_text(encoding="utf-8") == "keep\n"


def test_deploy_succeeds_before_open_when_ready(tmp_path: Path) -> None:
    clock = SimClock(PRE)
    result = deploy(
        "newsha",
        state_dir=tmp_path,
        clock=clock,
        ready_timeout_s=2.0,
        start_engine=lambda: write_engine_status(tmp_path, clock),
    )
    assert result["ok"] is True and result["sha"] == "newsha"


def test_restore_reproduces_output_hash(tmp_path: Path) -> None:
    day = tmp_path / "day"
    snap = tmp_path / "snap"
    restored = tmp_path / "restored"
    day.mkdir()
    (day / "engine_status.json").write_text(
        '{"status":"READY","session":"2026-09-28"}\n', encoding="utf-8"
    )
    (day / "trades").write_text("t1\n", encoding="utf-8")
    digest = backup_state(day, snap)
    assert (snap / "output_hash").read_text(encoding="utf-8").strip() == digest
    (day / "trades").write_text("MUTATED\n", encoding="utf-8")
    got = restore_state(snap, restored)
    assert got == digest == output_hash(restored)
    assert (restored / "trades").read_text(encoding="utf-8") == "t1\n"


def test_run_with_deadline_times_out_without_partial(tmp_path: Path) -> None:
    dest = tmp_path / "out.txt"

    def hang() -> None:
        dest.write_text("partial\n", encoding="utf-8")
        raise RuntimeError("should not publish")  # pragma: no cover

    def slow() -> None:
        import time

        time.sleep(2)

    try:
        run_with_deadline(slow, 0.05, job="replay")
        raise AssertionError("expected JobTimeout")
    except JobTimeout as exc:
        assert exc.job == "replay"
    assert dest.exists() is False or dest.read_text(encoding="utf-8") != "published"


def test_job_registry_matches_ticket() -> None:
    assert set(JOBS) == {"replay", "forward-eval", "etl", "bench-legacy", "pre-market", "backup"}
    assert all(s > 0 for s in JOBS.values())


def test_dockerfile_is_non_root() -> None:
    df = (ROOT / "deploy" / "docker" / "Dockerfile").read_text(encoding="utf-8")
    compose = COMPOSE.read_text(encoding="utf-8")
    assert "USER aad" in df and "useradd" in df
    assert "read_only: true" in compose and 'user: "10001:10001"' in compose


def test_compose_up_replay_reaches_ready(tmp_path: Path) -> None:
    """Same command compose runs: engine --mode replay writes READY with no credentials."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("DHAN_") and k != "ALL_ABOUT_DHAN_LIVE_CONFIRM"
    }
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "runtime",
            "engine",
            "--once",
            "--mode",
            "replay",
            "--state-dir",
            str(tmp_path),
            "--now",
            PRE.isoformat(),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    body = json.loads((tmp_path / "engine_status.json").read_text(encoding="utf-8"))
    assert body["status"] == "READY" and body["recon_ok"] is True
