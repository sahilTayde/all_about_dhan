"""V2 .venv-v2 must ship PyYAML so accounts.yaml loads (c5-start / accounts list)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def test_v2_spec_declares_pyyaml() -> None:
    accounts_pyproject = (REPO / "packages" / "accounts" / "pyproject.toml").read_text(encoding="utf-8")
    v2_in = (REPO / "requirements" / "v2.in").read_text(encoding="utf-8")
    v2_lock = (REPO / "requirements" / "v2.txt").read_text(encoding="utf-8")
    setup = (REPO / "scripts" / "mac_setup_v2.sh").read_text(encoding="utf-8")
    check = (REPO / "scripts" / "ci" / "check_v2_venv_accounts.sh").read_text(encoding="utf-8")
    assert "PyYAML>=6" in accounts_pyproject
    assert "PyYAML>=6" in v2_in
    assert "pyyaml==" in v2_lock.lower()
    assert "--require-hashes" in v2_lock or "--hash=" in v2_lock
    assert "requirements/v2.txt" in setup
    assert "--require-hashes" in setup
    assert "python -m accounts list" in setup
    assert "requirements/v2.txt" in check
    assert "accounts list" in check
    assert "packages/brokers" not in setup
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "check_v2_venv_accounts.sh" in ci
