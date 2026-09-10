"""Short-lived chain IV ticker: poll Dhan option chains, persist IV stats.

Founder-invoked market ticker (2026-09-10): run for N minutes during market
hours, one chain fetch per underlying per round, >=3s between Data-API calls
(documented option-chain rate limit). Persists per-day snapshots under
data/recon/chain_iv/ via trading_agents_india.chain_iv. Read-only market
data — no orders, no alerts, no strategy execution.

Usage: .venv/bin/python scripts/run_chain_iv_ticker.py --minutes 5 --interval 20
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "trading_agents_india" / "src"))

from trading_agents_india.chain_iv import gather_chain_iv, load_iv_stats, tilt_momentum
from trading_agents_india.session_clock import now_ist

UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")
CALL_SPACING_S = 3.5  # documented option-chain limit: 1 per 3s


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=5.0)
    parser.add_argument("--interval", type=float, default=20.0, help="seconds per full round")
    args = parser.parse_args()

    deadline = time.monotonic() + args.minutes * 60.0
    expiry_cache: dict[str, str] = {}
    rounds = 0
    print(f"chain_iv ticker start {now_ist().isoformat(timespec='seconds')} "
          f"for {args.minutes:g} min, round interval {args.interval:g}s", flush=True)

    while time.monotonic() < deadline:
        rounds += 1
        round_start = time.monotonic()
        for und in UNDERLYINGS:
            res = gather_chain_iv(und, prefer_live=True, expiry=expiry_cache.get(und))
            if res.stats:
                if res.stats.get("expiry"):
                    expiry_cache[und] = str(res.stats["expiry"])
                s = res.stats
                print(
                    f"[{s['as_of_ist']}] {und:9s} spot={s['spot']:.2f} atm={s['atm_strike']:.0f} "
                    f"tilt={s['skew_tilt']} curv={s['curvature']} entropy={s['iv_entropy']} "
                    f"(iv strikes {s['iv_present']}/{s['strike_count']})",
                    flush=True,
                )
            else:
                print(f"[{now_ist().isoformat(timespec='seconds')}] {und:9s} GAP: {res.data_gaps}", flush=True)
            time.sleep(CALL_SPACING_S)
        elapsed = time.monotonic() - round_start
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(max(0.0, min(args.interval - elapsed, remaining)))

    print(f"\n--- summary after {rounds} rounds ---", flush=True)
    for und in UNDERLYINGS:
        snaps = load_iv_stats(und)
        if not snaps:
            print(f"{und:9s} no snapshots persisted")
            continue
        last = snaps[-1]
        mom = tilt_momentum(snaps, lookback=3)
        print(
            f"{und:9s} snapshots={len(snaps)} last tilt={last.get('skew_tilt')} "
            f"curv={last.get('curvature')} entropy={last.get('iv_entropy')} "
            f"tilt_momentum(3)={mom}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
