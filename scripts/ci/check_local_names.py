#!/usr/bin/env python3
"""Dependency-confusion guard: every in-repo distribution must be installed from this checkout.

Bare local names (desk, brokers, ledger, events, ...) exist or could exist on PyPI. CI installs
them with ``pip install --no-deps -e <folder>``; this check fails if any of them resolved from an
index instead, or if a pyproject depends on a local name without the ``+aad`` local pin.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def local_projects() -> dict[str, Path]:
    out = {}
    for pyproject in sorted(ROOT.glob("packages/*/pyproject.toml")) + [ROOT / "apps" / "api" / "pyproject.toml"]:
        project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project") or {}
        if project.get("name"):
            out[_norm(project["name"])] = pyproject.parent
    return out


def main() -> int:
    projects = local_projects()
    problems = []
    for name, folder in projects.items():
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            problems.append(f"{name}: not installed")
            continue
        raw = dist.read_text("direct_url.json")
        url = json.loads(raw).get("url", "") if raw else ""
        if not url.startswith("file://") or Path(url[len("file://"):]).resolve() != folder.resolve():
            problems.append(f"{name}: installed from {url or 'a package index'}, expected {folder}")
    for name, folder in projects.items():
        deps = (tomllib.loads((folder / "pyproject.toml").read_text(encoding="utf-8")).get("project") or {}).get("dependencies") or []
        for dep in deps:
            dep_name = _norm(re.split(r"[<>=!~\[; ]", dep, maxsplit=1)[0])
            if dep_name in projects and "+aad" not in dep:
                problems.append(f"{name} depends on local {dep_name} without the +aad pin: {dep!r}")
    for p in problems:
        print(f"LOCAL-NAME GUARD: {p}")
    print(f"{len(projects)} local distributions checked; {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
