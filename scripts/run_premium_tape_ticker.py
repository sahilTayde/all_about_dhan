"""Premium-tape ticker: refresh rolling 1m option tape periodically.

Each round fetches ce+pe for every (underlying, strike label) pair via the
documented rollingoption endpoint (which backfills the whole day, so missed
rounds self-heal). Labels are the documented ATM / ATM+N / ATM-N (verified
live 2026-09-11 with per-bar strike cross-check); see premium_tape.py.

Usage: .venv/bin/python scripts/run_premium_tape_ticker.py --minutes 255 --interval 900
Read-only market data. No orders.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "trading_agents_india" / "src"))

from trading_agents_india.premium_tape import gather_premium_tape
from trading_agents_india.session_clock import now_ist

UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")
STRIKE_LABELS = ("ATM", "ATM+1", "ATM-1")  # ATM plus one step OTM/ITM each side
CALL_SPACING_S = 1.0  # rollingoption sits under the 5 req/s Data-API budget


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=255.0)
    parser.add_argument("--interval", type=float, default=900.0, help="seconds per full round")
    args = parser.parse_args()

    deadline = time.monotonic() + args.minutes * 60.0
    rounds = 0
    print(f"premium tape ticker start {now_ist().isoformat(timespec='seconds')} "
          f"for {args.minutes:g} min, round interval {args.interval:g}s", flush=True)
    while True:
        rounds += 1
        round_start = time.monotonic()
        for und in UNDERLYINGS:
            for label in STRIKE_LABELS:
                res = gather_premium_tape(und, prefer_live=True, strike_label=label)
                stamp = now_ist().isoformat(timespec="seconds")
                if res.source == "dhan_rollingoption_1m":
                    print(f"[{stamp}] {und:9s} {label:5s} ce={res.ce_count} pe={res.pe_count}", flush=True)
                else:
                    print(f"[{stamp}] {und:9s} {label:5s} GAP: {res.data_gaps}", flush=True)
                time.sleep(CALL_SPACING_S)
        if time.monotonic() >= deadline:
            break
        elapsed = time.monotonic() - round_start
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(max(0.0, min(args.interval - elapsed, remaining)))
    print(f"done after {rounds} rounds at {now_ist().isoformat(timespec='seconds')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
