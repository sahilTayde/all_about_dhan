"""python -m ledger migrate --path FILE [--allow-legacy]. Paper only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ledger.migrate import CODE_SCHEMA_VERSION, migrate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ledger v2 migrations (explicit; never auto on legacy path)")
    p.add_argument("command", choices=("migrate",))
    p.add_argument("--path", required=True, help="SQLite file (not the Monday engine default unless --allow-legacy)")
    p.add_argument("--allow-legacy", action="store_true")
    args = p.parse_args(argv)
    ver = migrate(Path(args.path), allow_legacy=args.allow_legacy)
    print(json.dumps({"ok": True, "schema_version": ver, "code_version": CODE_SCHEMA_VERSION}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
