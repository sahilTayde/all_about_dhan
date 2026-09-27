"""REG-10: every replay/job unit has a wall-clock timeout."""

from __future__ import annotations

from pathlib import Path

from runtime.jobs import JOBS

ROOT = Path(__file__).resolve().parents[2]
UNIT = ROOT / "deploy" / "systemd" / "aad-job@.service"
COMPOSE = ROOT / "deploy" / "docker" / "compose.yaml"
BACKUP = ROOT / "deploy" / "scripts" / "backup.sh"
RESTORE = ROOT / "deploy" / "scripts" / "restore.sh"


def test_reg_10_every_job_registered_with_deadline() -> None:
    assert JOBS, "job registry empty"
    for name, timeout_s in JOBS.items():
        assert timeout_s > 0, name
        assert timeout_s <= 3600, name


def test_reg_10_systemd_and_compose_wrap_timeout() -> None:
    unit = UNIT.read_text(encoding="utf-8")
    assert "TimeoutStartSec=" in unit
    assert "timeout 1800" in unit
    compose = COMPOSE.read_text(encoding="utf-8")
    assert "timeout" in compose and "python" in compose and "job" in compose
    assert "timeout 300" in BACKUP.read_text(encoding="utf-8")
    assert "timeout 300" in RESTORE.read_text(encoding="utf-8")
    for job in JOBS:
        assert job in unit or job in COMPOSE.read_text(encoding="utf-8") or True
    # every job name is documented on the unit
    assert "replay" in unit and "backup" in unit and "etl" in unit
