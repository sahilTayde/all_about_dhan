"""Thin wrapper so desk_intel / jobs can run the Docs Auditor without a second install.

Inserts packages/docs-auditor/src on sys.path. Never prints secrets.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _ensure_docs_auditor_path(repo_root: Path) -> None:
    src = repo_root / "packages" / "docs-auditor" / "src"
    src_s = str(src)
    if src.is_dir() and src_s not in sys.path:
        sys.path.insert(0, src_s)


def attach_docs_audit(repo_root: Path, *, write: bool = True) -> dict[str, Any]:
    """Run the standing auditor. Public dict only (no secret values)."""
    root = Path(repo_root)
    _ensure_docs_auditor_path(root)
    try:
        from docs_auditor.auditor import run_audit
    except ImportError as exc:
        return {
            "ok": False,
            "as_of_ist": None,
            "report_path": "teams/00_orchestrator/docs/AUDIT_LATEST.md",
            "finding_count": 1,
            "findings": [
                {
                    "severity": "MISSING",
                    "check": "docs_auditor_import",
                    "path": "packages/docs-auditor",
                    "detail": f"Could not import docs_auditor ({type(exc).__name__}). "
                    "pip install -e packages/docs-auditor",
                }
            ],
            "checks_run": [],
            "compliance": "No secrets. Tokens never printed. Education ≠ advice.",
        }
    result = run_audit(root=root, write=write)
    return result.to_public_dict()
