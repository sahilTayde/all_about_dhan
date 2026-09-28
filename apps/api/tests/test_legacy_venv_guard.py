"""P0 Mac run: API stays up when events/v2_gateway are missing (Python 3.9 .venv)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[3]
API_SRC = REPO / "apps" / "api" / "src"

_BLOCK_IMPORT = r"""
import json
import sys

class Block:
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".", 1)[0]
        if root in {"events", "contracts"} or fullname == "api.v2_gateway":
            raise ImportError("blocked " + fullname)
        return None

sys.meta_path.insert(0, Block())
for name in list(sys.modules):
    if name == "api.main" or name.startswith("api.v2_gateway") or name.startswith("events"):
        del sys.modules[name]
from api.main import V2_GATEWAY_AVAILABLE, create_app
from fastapi.testclient import TestClient
"""


def _run_blocked(snippet: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(API_SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-c", _BLOCK_IMPORT + snippet],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_legacy_api_imports_when_events_missing() -> None:
    proc = _run_blocked(
        """
assert V2_GATEWAY_AVAILABLE is False
app = create_app()
assert not any(getattr(r, "path", "").startswith("/v2") for r in app.routes)
print("import_ok")
"""
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "import_ok" in proc.stdout


def test_a_founder_book_identical_without_v2() -> None:
    """Legacy /paper/founder-book shape is unchanged when v2 routes are off."""
    from api.main import create_app as create_with_v2

    with_v2 = TestClient(create_with_v2()).get("/paper/founder-book")
    assert with_v2.status_code == 200
    expected_keys = set(with_v2.json())

    proc = _run_blocked(
        """
assert V2_GATEWAY_AVAILABLE is False
client = TestClient(create_app())
r = client.get("/paper/founder-book")
assert r.status_code == 200, r.text
body = r.json()
assert body["orders"] == "REFUSED"
assert body["promote"] is False
assert "trade_underlyings" in body
assert "known_underlyings" in body
assert client.get("/v2/snapshot").status_code == 404
print(json.dumps(sorted(body.keys())))
"""
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    got_keys = set(json.loads(proc.stdout.strip().splitlines()[-1]))
    assert got_keys == expected_keys


def test_a_v2_routes_still_mount_when_events_installed() -> None:
    try:
        from api.v2_gateway import attach_gateway
    except ImportError:
        pytest.skip("events/v2_gateway extras not installed in this venv")
    from api.main import V2_GATEWAY_AVAILABLE, create_app

    assert attach_gateway is not None
    assert V2_GATEWAY_AVAILABLE is True
    client = TestClient(create_app())
    body = client.get("/v2/snapshot").json()
    assert body["v2"] is True
    assert body["orders"] == "REFUSED"
    assert client.get("/paper/founder-book").status_code == 200
