"""python -m health [--once] — run the health monitor (every 60 s by default)."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from health.monitor import HealthMonitor


def main() -> None:
    p = argparse.ArgumentParser(description="all_about_dhan health alarms (read-only)")
    p.add_argument("--once", action="store_true", help="run all checks once, print status, exit")
    p.add_argument("--interval", type=float, default=60.0, help="seconds between runs")
    p.add_argument("--recon-dir", type=Path, default=Path("data/recon"))
    p.add_argument("--ledger", type=Path, default=Path("data/ledger/ledger.sqlite"))
    p.add_argument("--health-dir", type=Path, default=Path("data/health"))
    p.add_argument("--min-free-gb", type=float, default=2.0)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    monitor = HealthMonitor(args.recon_dir, args.ledger, args.health_dir, min_free_gb=args.min_free_gb)
    if args.once:
        print(json.dumps(monitor.run_once(), indent=2))
    else:
        monitor.run_forever(args.interval)


if __name__ == "__main__":
    main()
