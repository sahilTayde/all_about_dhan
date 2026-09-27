"""python -m runtime <command> — frozen legacy benchmark entry.

python -m runtime bench-legacy --day YYYY-MM-DD --tape PATH [--out DIR]
"""

from __future__ import annotations

import sys

from runtime.bench_legacy import main as bench_legacy_main


def main(argv: list[str] | None = None) -> int:
    """Dispatch `python -m runtime` subcommands."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print("usage: python -m runtime bench-legacy --day YYYY-MM-DD --tape PATH [--out DIR] [--deadline SECONDS]")
        return 0
    if args[0] != "bench-legacy":
        print(f"error: unknown command {args[0]!r} (expected bench-legacy)", file=sys.stderr)
        return 2
    return bench_legacy_main(args[1:])


if __name__ == "__main__":
    sys.exit(main())
