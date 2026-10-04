"""Default path never constructs a live Dhan client. Source + import isolation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from harness.broker import live_ctor_calls, make_broker
from harness.gates import APPROVAL_ENV, APPROVAL_VALUE, EXIT_REFUSED, HarnessRefused
from harness.run import run_shadow_test

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "packages" / "harness" / "src"


def test_make_broker_default_refuses_and_does_not_build_live() -> None:
    before = live_ctor_calls()
    with pytest.raises(HarnessRefused) as info:
        make_broker()
    assert info.value.reason_code == "TRANSPORT_OFF"
    assert live_ctor_calls() == before


def test_make_broker_mock_is_not_live() -> None:
    before = live_ctor_calls()
    broker = make_broker(transport="mock")
    assert broker.is_live is False
    assert broker.name == "mock"
    assert live_ctor_calls() == before


def test_run_without_injected_broker_default_transport_refuses() -> None:
    env = {
        APPROVAL_ENV: APPROVAL_VALUE,
        "DHAN_CLIENT_ID": "test-client",
        "DHAN_ACCESS_TOKEN": "test-token",
    }
    before = live_ctor_calls()
    with pytest.raises(HarnessRefused) as info:
        run_shadow_test(mode="shadow", env=env, transport="none")
    assert info.value.reason_code == "TRANSPORT_OFF"
    assert live_ctor_calls() == before


def test_sources_never_construct_dhanbroker_or_import_oms() -> None:
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "DhanBroker(" not in text, path
        assert "from brokers.dhan" not in text, path
        assert "import brokers.dhan" not in text, path
        assert "from oms.router" not in text, path
        assert "from desk_ml.paper_scalp" not in text, path
        assert "V2_LIVE_BROKERS_ENABLED = True" not in text, path
        assert "I_UNDERSTAND_REAL_MONEY" not in text, path


def test_importing_harness_does_not_load_live_modules() -> None:
    script = r"""
import sys

class _BlockLive:
    def find_spec(self, fullname, path=None, target=None):
        banned = (
            "harness.dhan_live",
            "dhan_client.rest",
            "dhan_client.execution",
            "brokers.dhan",
        )
        if fullname in banned or any(fullname.startswith(b + ".") for b in banned):
            raise ModuleNotFoundError(fullname)
        return None

sys.meta_path.insert(0, _BlockLive())
import harness
from harness.broker import make_broker, live_ctor_calls
from harness.gates import HarnessRefused
assert harness.run_shadow_test is not None
assert live_ctor_calls() == 0
try:
    make_broker()
except HarnessRefused as exc:
    assert exc.reason_code == "TRANSPORT_OFF"
else:
    raise SystemExit("default make_broker must refuse")
assert "harness.dhan_live" not in sys.modules
assert "dhan_client.rest" not in sys.modules
assert "brokers.dhan" not in sys.modules
print("ok")
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok" in proc.stdout


def test_default_cli_is_off() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "harness"],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env={k: v for k, v in __import__("os").environ.items() if not k.startswith("DHAN_")},
    )
    assert proc.returncode == EXIT_REFUSED
    assert "harness refused" in proc.stderr
    assert "test-token" not in proc.stderr
    assert "I_APPROVE" not in proc.stdout
