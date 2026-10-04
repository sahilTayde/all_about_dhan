"""CLI: default OFF; mock path after gates; no traceback secrets."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from harness.__main__ import main
from harness.gates import APPROVAL_ENV, APPROVAL_VALUE, EXIT_OK, EXIT_ORDER_PATH, EXIT_REFUSED

REPO = Path(__file__).resolve().parents[3]


def _clean_env(**extra: str) -> dict[str, str]:
    out = {k: v for k, v in os.environ.items() if not k.startswith("DHAN_") and k != APPROVAL_ENV}
    out.update(extra)
    return out


def test_cli_refuses_without_approval() -> None:
    assert main(["--mode", "shadow", "--transport", "mock"]) == EXIT_REFUSED


def test_cli_refuses_live_mode() -> None:
    assert main(["--mode", "live", "--transport", "mock"]) == EXIT_REFUSED


def test_cli_mock_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(APPROVAL_ENV, APPROVAL_VALUE)
    monkeypatch.setenv("DHAN_CLIENT_ID", "test-client")
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "test-token")
    assert main(["--mode", "shadow", "--transport", "mock"]) == EXIT_OK


def test_cli_dhan_without_security_id_refuses() -> None:
    assert main(["--mode", "shadow", "--transport", "dhan"]) == EXIT_REFUSED


def test_cli_marketable_price_refused() -> None:
    rc = main(["--mode", "shadow", "--transport", "mock", "--limit-price", "50"])
    assert rc == EXIT_ORDER_PATH


def test_subprocess_default_no_traceback_secrets() -> None:
    env = _clean_env()
    env["DHAN_ACCESS_TOKEN"] = "super-secret-token-value"
    proc = subprocess.run(
        [sys.executable, "-m", "harness", "--mode", "shadow", "--transport", "dhan"],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env=env,
    )
    assert proc.returncode == EXIT_REFUSED
    blob = proc.stdout + proc.stderr
    assert "Traceback" not in blob
    assert "super-secret-token-value" not in blob
    assert "harness refused" in proc.stderr
