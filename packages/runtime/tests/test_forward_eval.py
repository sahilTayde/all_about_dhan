"""V2-20a CLI: disabled by default; REG-10 deadline."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from runtime.forward_eval import forward_eval_enabled
from runtime.forward_eval import main as forward_eval_main
from runtime.jobs import JOBS, JobTimeout, run_with_deadline

ROOT = Path(__file__).resolve().parents[3]


def test_disabled_by_default_exits_0_doing_nothing(tmp_path: Path) -> None:
    assert forward_eval_enabled(ROOT / "config" / "v2" / "engine.yaml") is False
    proc = subprocess.run(
        [sys.executable, "-m", "runtime", "forward-eval", "--session", "2026-09-28"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout.strip().splitlines()[-1])
    assert body["ok"] is True
    assert body["skipped"] is True
    assert body["reason"] == "forward_eval.enabled: false"
    assert list(tmp_path.iterdir()) == []


def test_reg_10_forward_eval_runs_under_deadline() -> None:
    assert JOBS["forward-eval"] == 1800

    def slow() -> None:
        time.sleep(10)

    try:
        run_with_deadline(slow, 0.2, job="forward-eval")
        raise AssertionError("expected JobTimeout")
    except JobTimeout as exc:
        assert exc.job == "forward-eval"


def test_reg_10_enabled_cli_times_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "engine.yaml"
    cfg.write_text("forward_eval:\n  enabled: true\n", encoding="utf-8")
    tape = tmp_path / "t.jsonl"
    tape.write_text("{}\n", encoding="utf-8")

    def sleepy(**kwargs: object) -> dict[str, object]:
        time.sleep(10)
        return {}

    import runtime.forward_eval as fe

    monkeypatch.setattr(fe, "run_forward_eval", sleepy)
    rc = forward_eval_main(
        [
            "--session",
            "2026-09-28",
            "--tape",
            str(tape),
            "--config",
            str(cfg),
            "--out",
            str(tmp_path / "out"),
            "--deadline",
            "0.2",
        ]
    )
    assert rc == 1
    assert not (tmp_path / "out" / "forward_report.json").exists()


def test_help_lists_forward_eval() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "runtime", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "forward-eval" in proc.stdout


def test_enabled_config_is_opt_in(tmp_path: Path) -> None:
    src = yaml.safe_load((ROOT / "config" / "v2" / "engine.yaml").read_text(encoding="utf-8"))
    assert src["forward_eval"]["enabled"] is False
    on = tmp_path / "on.yaml"
    on.write_text("forward_eval:\n  enabled: true\n", encoding="utf-8")
    assert forward_eval_enabled(on) is True
