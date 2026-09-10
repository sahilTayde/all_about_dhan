"""Repo paths. Never print secrets."""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_BASENAMES = frozenset(
    {
        "transcripts.sqlite",
        "trading_agents_india.sqlite",
        "agent_rag.sqlite",
    }
)


def repo_root() -> Path:
    # packages/warehouse/src/warehouse/paths.py → repo root
    return Path(__file__).resolve().parents[4]


def default_db(root: Path | None = None) -> Path:
    return (root or repo_root()) / "data" / "knowledge" / "warehouse.sqlite"


def assert_writable_db(path: Path) -> Path:
    """Refuse well-known other KBs so a bad path cannot overwrite them."""
    name = path.name.lower()
    if name in FORBIDDEN_BASENAMES:
        raise ValueError(f"refusing to open protected knowledge file: {path.name}")
    return path
