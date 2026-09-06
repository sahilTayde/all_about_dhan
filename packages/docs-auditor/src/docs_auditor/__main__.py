"""CLI: python -m docs_auditor

Never prints secret values. Local files only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from docs_auditor.auditor import run_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docs_auditor",
        description=(
            "Standing Docs Auditor (09_review). Compare requirements vs code/config. "
            "No web scrape. Never prints secrets. Exit 0 pass / 1 stale."
        ),
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Repo root (default: walk up from cwd until AGENT.md + config/workspace.yaml).",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write teams/00_orchestrator/docs/AUDIT_LATEST.md.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a public JSON summary (paths + flags only, no secret values).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve() if args.root else None
    result = run_audit(root=root, write=not args.no_write)
    payload = result.to_public_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(result.console_summary())
        if not result.ok:
            for item in result.findings:
                print(f"  {item.severity:12} {item.check:24} {item.path}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
