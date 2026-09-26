"""A clean venv, with PYTHONPATH unset, can import the paper desk. In-repo packages never come from PyPI.

packages/indicators and packages/contracts are notes only (no Python package).
The clean-venv tests need the network (pip) and skip when offline. The pin check does not.
"""

import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")  # Python 3.11+

REPO = Path(__file__).resolve().parents[3]
LOCAL = "0.1.0+aad"


def _online() -> bool:
    try:
        socket.create_connection(("pypi.org", 443), timeout=3).close()
        return True
    except OSError:
        return False

# Same editable set as .cursor/install.sh, without apps/api (that app is not under packages/).
PACKAGES = (
    "packages/dhan-client",
    "packages/backtest",
    "packages/ledger",
    "packages/risk-engine",
    "packages/brokers",
    "packages/health",
    "packages/data-recorder",
    "packages/desk-intel",
    "packages/docs-auditor",
    "packages/agent_rag",
    "packages/warehouse",
    "packages/trading_agents_india",
    "packages/events",
    "packages/desk-ml",
    "packages/analysts",
    "packages/boss",
    "packages/desk",
)


def _projects() -> dict[str, tuple[Path, dict]]:
    root = tomllib.loads((REPO / "pyproject.toml").read_text())
    out = {}
    for rel in root["tool"]["uv"]["workspace"]["members"]:
        data = tomllib.loads((REPO / rel / "pyproject.toml").read_text())
        out[data["project"]["name"]] = (REPO / rel, data)
    return out


def _dep_name(spec: str) -> str:
    return re.split(r"[\s<>=!~\[;@]", spec, maxsplit=1)[0].lower()


def test_in_repo_dependencies_cannot_resolve_from_pypi():
    """Every in-repo dependency pins a +aad local version (PyPI refuses those uploads) and has a uv
    workspace source. A standalone pip install then fails instead of fetching a look-alike."""
    projects = _projects()
    assert set(PACKAGES) <= {str(p.relative_to(REPO)) for p, _d in projects.values()}
    seen = 0
    for name, (_path, data) in projects.items():
        sources = data.get("tool", {}).get("uv", {}).get("sources", {})
        for spec in data["project"].get("dependencies", []):
            dep = _dep_name(spec)
            if dep not in projects:
                continue
            seen += 1
            assert spec.replace(" ", "").lower() == f"{dep}=={LOCAL}", f"{name}: {spec}"
            assert projects[dep][1]["project"]["version"] == LOCAL, dep
            assert sources.get(dep) == {"workspace": True}, f"{name}: {dep} has no uv workspace source"
    assert seen >= 10


def _venv(tmp_path: Path) -> tuple[Path, dict]:
    venv = tmp_path / "venv"
    subprocess.check_call([sys.executable, "-m", "venv", str(venv)], cwd=REPO)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    py = venv / "bin" / "python"
    subprocess.check_call([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"], cwd=REPO, env=env)
    return py, env


@pytest.mark.network
def test_clean_venv_installs_every_package_and_imports_desk(tmp_path):
    if not _online():
        pytest.skip("offline: clean-venv install needs network")
    py, env = _venv(tmp_path)
    report = tmp_path / "report.json"
    install = [str(py), "-m", "pip", "install", "--report", str(report)]
    for rel in PACKAGES:
        install.extend(["-e", rel])
    subprocess.check_call(install, cwd=REPO, env=env)
    internal = set(_projects())
    for item in json.loads(report.read_text())["install"]:
        name = item["metadata"]["name"].lower()
        if name in internal:
            url = item["download_info"]["url"]
            assert url.startswith("file://") and str(REPO) in url, f"{name} came from {url}"
    probe = (
        "import brokers, risk_engine, ledger, desk, desk_ml, events, analysts, boss, health, data_recorder\n"
        "import trading_agents_india\n"
        "from desk_ml.event_path import EVENT_BUS_INSTALL\n"
        "assert 'packages/brokers' in EVENT_BUS_INSTALL\n"
        "assert 'packages/risk-engine' in EVENT_BUS_INSTALL\n"
        "assert 'packages/ledger' in EVENT_BUS_INSTALL\n"
        "assert 'packages/trading_agents_india' in EVENT_BUS_INSTALL\n"
    )
    subprocess.check_call([str(py), "-c", probe], cwd=tmp_path, env=env)


@pytest.mark.network
def test_standalone_install_refuses_instead_of_fetching_from_pypi(tmp_path):
    if not _online():
        pytest.skip("offline: needs network to ask PyPI")
    py, env = _venv(tmp_path)
    run = subprocess.run(
        [str(py), "-m", "pip", "install", "--dry-run", "-e", "packages/desk-ml"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    assert run.returncode != 0
    assert f"trading-agents-india=={LOCAL}" in (run.stdout + run.stderr)
