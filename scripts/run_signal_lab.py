"""Run the signal-lab grid over persisted premium-tape days and summarize.

Usage:
  .venv/bin/python scripts/run_signal_lab.py --days 2026-09-09 2026-09-10

Writes per-run JSON (records + summary) to data/recon/signal_lab/ and prints
ranked summary tables. Research-only: gross premium points, no fills/costs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "trading_agents_india" / "src"))

from trading_agents_india.premium_tape import load_tape_bars
from trading_agents_india.session_clock import now_ist
from trading_agents_india.signal_lab import (
    GATES,
    OVERLAYS,
    TIMEFRAMES,
    evaluate_combo,
    summarize,
)

UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")
SIDES = ("ce", "pe")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", nargs="+", required=True)
    parser.add_argument("--min-signals", type=int, default=5, help="hide combos with fewer signals in the ranked view")
    args = parser.parse_args()

    records = []
    coverage = []
    for day in args.days:
        for und in UNDERLYINGS:
            for side in SIDES:
                bars = load_tape_bars(und, day=day, side=side)
                coverage.append(f"{day} {und} {side}: {len(bars)} bars")
                if len(bars) < 60:
                    continue
                for tf in TIMEFRAMES:
                    for gate in GATES:
                        for overlay in OVERLAYS:
                            records += evaluate_combo(
                                bars, day=day, underlying=und, side=side,
                                timeframe=tf, gate=gate, overlay=overlay,
                            )

    print("Coverage:")
    for line in coverage:
        print(" ", line)
    print(f"\nTotal signals across grid: {len(records)}")

    rows = summarize(records)
    ranked = [r for r in rows if r["signals"] >= args.min_signals and r["avg_shell_pl_pct"] is not None]
    ranked.sort(key=lambda r: r["avg_shell_pl_pct"], reverse=True)

    header = (
        f"{'tf':>3} {'gate':<10} {'overlay':<6} {'n':>4} {'pos15':>5} "
        f"{'avg%15m':>8} {'avg%30m':>8} {'mae%30m':>8} {'shell%':>7}"
    )
    print("\nRanked combos by SL25/TP50 shell P/L (min", args.min_signals, "signals):")
    print(header)
    for r in ranked:
        print(
            f"{r['timeframe']:>3} {r['gate']:<10} {r['overlay']:<6} {r['signals']:>4} "
            f"{r['pos_15m']:>5} {str(r['avg_ret_pct_15m']):>8} {str(r['avg_ret_pct_30m']):>8} "
            f"{str(r['avg_mae_pct_30m']):>8} {str(r['avg_shell_pl_pct']):>7}"
        )

    out_dir = Path("data/recon/signal_lab")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_ist().strftime("%Y-%m-%d_%H%M")
    out_path = out_dir / f"signal_lab_{stamp}.json"
    out_path.write_text(
        json.dumps(
            {
                "meta": {
                    "run_at_ist": now_ist().isoformat(timespec="seconds"),
                    "days": args.days,
                    "note": "Gross premium points, rolling ATM tape, no fills/costs. Research only.",
                },
                "summary": rows,
                "records": [r.to_dict() for r in records],
            }
        ),
        encoding="utf-8",
    )
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
