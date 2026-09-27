"""CLI: python -m premarket  (advisory; exit 0 even when every source is missing).

python -m premarket                                   # live free sources, writes data/premarket/
python -m premarket --offline                         # no network: local sources only
python -m premarket --fixtures packages/premarket/fixtures/synthetic --date 2026-09-28 --now 2026-09-28T08:30:00+05:30
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from premarket.service import (
    build_context,
    load_config,
    render_brief,
    repo_root,
    write_outputs,
)
from premarket.sources import FixtureFetcher, NoNetworkFetcher


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m premarket",
        description="Pre-market context + brief (advisory only).",
    )
    ap.add_argument("--market", default="india_index")
    ap.add_argument("--config", type=Path, help="default config/premarket.yaml")
    ap.add_argument(
        "--root", type=Path, help="data root for local sources (default: this checkout)"
    )
    net = ap.add_mutually_exclusive_group()
    net.add_argument(
        "--fixtures",
        type=Path,
        help="read canned responses from this folder instead of the network",
    )
    net.add_argument(
        "--offline", action="store_true", help="no network; only local sources run"
    )
    ap.add_argument(
        "--date",
        type=date.fromisoformat,
        help="session date (default: today in the market timezone)",
    )
    ap.add_argument(
        "--now", type=datetime.fromisoformat, help="clock override (ISO, with offset)"
    )
    ap.add_argument("--out-dir", type=Path, help="default <root>/data/premarket")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument(
        "--print", dest="show", choices=("brief", "json", "none"), default="brief"
    )
    args = ap.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except (OSError, ValueError) as exc:
        print(f"premarket: bad config: {exc}", file=sys.stderr)
        return 2
    root = (args.root or repo_root()).resolve()
    fetcher = (
        FixtureFetcher(args.fixtures)
        if args.fixtures
        else NoNetworkFetcher()
        if args.offline
        else None
    )
    try:
        ctx = build_context(
            args.market,
            config=cfg,
            fetcher=fetcher,
            root=root,
            now=args.now,
            session_date=args.date,
        )
    except ValueError as exc:
        print(f"premarket: {exc}", file=sys.stderr)
        return 2
    if not args.no_write:
        ctx["written"] = write_outputs(ctx, args.out_dir or root / "data" / "premarket")
    if args.show == "brief":
        print(render_brief(ctx), end="")
    elif args.show == "json":
        print(json.dumps(ctx, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
