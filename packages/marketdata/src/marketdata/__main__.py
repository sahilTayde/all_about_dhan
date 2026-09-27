"""CLI entry point for market data recorder.

Usage:
    python -m marketdata --record-only [--underlying NIFTY]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dhan_client.config import load_settings
from dhan_client.errors import CredentialsError

from marketdata.config import RecorderConfig
from marketdata.recorder import MarketDataRecorder
from marketdata.utils import resolve_repo_root


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Market data recorder (V2-D2)")
    parser.add_argument(
        "--record-only",
        action="store_true",
        help="Record mode (no engine)",
    )
    parser.add_argument(
        "--underlying",
        default="NIFTY",
        choices=["NIFTY", "BANKNIFTY", "SENSEX"],
        help="Underlying to track",
    )
    parser.add_argument(
        "--tape-root",
        type=Path,
        default=None,
        help="Tape root directory (default: data/tape/v2 from repo root)",
    )

    args = parser.parse_args()

    if not args.record_only:
        print("Only --record-only mode is supported in V2-D2")
        sys.exit(1)

    # Load settings with credentials check
    try:
        settings = load_settings(dry_run=False)
    except CredentialsError as e:
        print(f"ERROR: Missing credentials. Please set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN")
        print(f"Set them in environment variables or in .env file in repo root")
        sys.exit(1)

    # Resolve tape root from repo root if not specified
    if args.tape_root is None:
        repo_root = resolve_repo_root()
        tape_root = repo_root / "data" / "tape" / "v2"
    else:
        tape_root = args.tape_root

    config = RecorderConfig(
        tape_root=tape_root,
        underlying=args.underlying,
    )

    recorder = MarketDataRecorder(config, settings)

    print(f"Starting market data recorder for {args.underlying}")
    print(f"Tape root: {tape_root}")
    print(f"Mode: {'DRY_RUN' if settings.dry_run else 'LIVE'}")
    print(f"Recording until 15:30 IST (Ctrl-C to stop early)")

    try:
        asyncio.run(recorder.run())
    except KeyboardInterrupt:
        print("\nStopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
