"""Test fixtures for trading_agents_india (REG-11 compliance)."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _redirect_repo_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Redirect _repo_root() in premium_tape and chain_iv to tmp_path.

    REG-11: tests must not write to data/. premium_tape.tape_dir() hard-codes
    _repo_root()/data/recon/premium_tape and mkdirs it. This fixture redirects
    all _repo_root() calls to tmp_path so tape writes go to tmp_path/data/...
    """
    from trading_agents_india import chain_iv, premium_tape

    monkeypatch.setattr(premium_tape, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(chain_iv, "_repo_root", lambda: tmp_path)
