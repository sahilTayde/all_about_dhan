"""Repo-root discovery. Does not open `.env`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

REPORT_REL = Path("teams/00_orchestrator/docs/AUDIT_LATEST.md")
MASTER_REL = Path("docs/MASTER_REQUIREMENTS.md")
STUB_MARKER = "STUB — manager sheet does not exist yet"


def find_repo_root(start: Optional[Path] = None) -> Path:
    here = (start or Path.cwd()).resolve()
    if here.is_file():
        here = here.parent
    for candidate in [here, *here.parents]:
        if (candidate / "AGENT.md").is_file() and (candidate / "config" / "workspace.yaml").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate repo root (expected AGENT.md and config/workspace.yaml)."
    )


def read_text(root: Path, rel: str) -> Optional[str]:
    path = root / rel
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")
