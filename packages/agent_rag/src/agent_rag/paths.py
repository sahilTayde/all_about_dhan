"""Repo paths. Never print secrets."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    # packages/agent_rag/src/agent_rag/paths.py → repo root
    return Path(__file__).resolve().parents[4]


def load_dotenv() -> None:
    env_path = repo_root() / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv as _ld

        _ld(env_path)
    except ImportError:
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw = line.split("=", 1)
            key = key.strip()
            val = raw.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def agent_rag_db(root: Path | None = None) -> Path:
    return (root or repo_root()) / "data" / "knowledge" / "agent_rag.sqlite"


def transcripts_db(root: Path | None = None) -> Path:
    """Reference only — agent_rag must never open this for writes."""
    return (root or repo_root()) / "data" / "knowledge" / "transcripts.sqlite"
