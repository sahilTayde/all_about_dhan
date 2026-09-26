"""A clean venv, with PYTHONPATH unset, can import the paper desk.

packages/indicators and packages/contracts are notes only (no Python package).
"""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

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


def test_clean_venv_installs_every_package_and_imports_desk(tmp_path):
    venv = tmp_path / "venv"
    subprocess.check_call([sys.executable, "-m", "venv", str(venv)], cwd=REPO)
    py = venv / "bin" / "python"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    cmd = [str(py), "-m", "pip", "install", "--upgrade", "pip"]
    subprocess.check_call(cmd, cwd=REPO, env=env)
    install = [str(py), "-m", "pip", "install"]
    for rel in PACKAGES:
        install.extend(["-e", rel])
    subprocess.check_call(install, cwd=REPO, env=env)
    probe = (
        "import brokers, risk_engine, ledger, desk, desk_ml, events, analysts, boss, health, data_recorder\n"
        "from desk_ml.event_path import EVENT_BUS_INSTALL\n"
        "assert 'packages/brokers' in EVENT_BUS_INSTALL\n"
        "assert 'packages/risk-engine' in EVENT_BUS_INSTALL\n"
        "assert 'packages/ledger' in EVENT_BUS_INSTALL\n"
    )
    subprocess.check_call([str(py), "-c", probe], cwd=tmp_path, env=env)
