"""CLI entry point for market data recorder.

Usage:
    python -m marketdata --record-only [--underlying NIFTY]
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dhan_client.config import Settings

from marketdata.config import RecorderConfig
from marketdata.recorder import MarketDataRecorder


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
        default=Path("data/tape/v2"),
        help="Tape root directory",
    )
    
    args = parser.parse_args()
    
    if not args.record_only:
        print("Only --record-only mode is supported in V2-D2")
        return
    
    # Check credentials
    settings = Settings()
    if not settings.dry_run and not settings.credentials.has_access:
        print("ERROR: Live mode requires DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN")
        print("Set environment variables or use --dry-run for testing")
        return
    
    config = RecorderConfig(
        tape_root=args.tape_root,
        underlying=args.underlying,
    )
    
    recorder = MarketDataRecorder(config, settings)
    
    print(f"Starting market data recorder for {args.underlying}")
    print(f"Tape root: {args.tape_root}")
    print(f"Mode: {'DRY_RUN' if settings.dry_run else 'LIVE'}")
    
    asyncio.run(recorder.run())


if __name__ == "__main__":
    main()
