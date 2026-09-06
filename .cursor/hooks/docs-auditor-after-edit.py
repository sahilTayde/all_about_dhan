#!/usr/bin/env python3
"""Remind the agent to run the Docs Auditor after requirement-file edits.

Reads postToolUse JSON on stdin. Never prints secrets. Never reads .env.
Never calls Dhan. Never scrapes the web.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

WATCH_NAMES = frozenset(
    {
        "AGENT.md",
        "PLAN.md",
        "HANDOFF.md",
        "MASTER_REQUIREMENTS.md",
        "workspace.yaml",
        "RETUNE_GATE.md",
        "SIGNAL_STAGING.md",
        "docs-auditor.mdc",
        "DOCS_AUDITOR.md",
        "TASK_DOCS_AUDITOR.md",
        "SDLC.md",
        "hooks.json",
    }
)

PATH_KEYS = frozenset(
    {
        "path",
        "file_path",
        "filepath",
        "filePath",
        "target_file",
        "target_notebook",
        "uri",
    }
)

REMINDER = (
    "You edited a requirements / HANDOFF / PLAN / workspace.yaml file. "
    "Before finishing, run `python -m docs_auditor` (or `python -m desk_intel audit-docs`) "
    "and do not merge if it exits 1. Nightly already runs the auditor last; that does not "
    "replace this after-edit run. Never print secrets."
)


def _walk_paths(obj: Any, acc: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key) in PATH_KEYS and isinstance(value, str) and value.strip():
                acc.append(value)
            else:
                _walk_paths(value, acc)
    elif isinstance(obj, list):
        for item in obj:
            _walk_paths(item, acc)


def _normalize(raw: str) -> str:
    text = raw.strip().replace("\\", "/")
    if text.startswith("file://"):
        text = text[7:]
    return text


def _is_watched(raw: str) -> bool:
    text = _normalize(raw)
    name = Path(text).name
    if name in WATCH_NAMES:
        return True
    lowered = f"/{text.lower()}"
    if "/cas/" in lowered and name.lower().endswith((".md", ".yaml", ".yml")):
        return True
    return False


def _emit(payload: dict[str, str]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))
    sys.stdout.write("\n")


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        _emit({})
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _emit({})
        return 0
    found: list[str] = []
    _walk_paths(data, found)
    if any(_is_watched(p) for p in found):
        _emit({"additional_context": REMINDER})
    else:
        _emit({})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Fail open: never block the agent on a reminder hook.
        sys.stdout.write("{}\n")
        raise SystemExit(0)
