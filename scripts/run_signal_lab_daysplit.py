"""Day-type split: grid results per day/side vs day character (drift + IV).

Answers: do the entry gates behave differently on trend/down days than on
flat-IV decay days? For each (day, underlying, side, strike label):
- day character: unconditional 15m drift, session move %, mean IV entropy
  and skew tilt (from chain_iv snapshots when available);
- grid: per-gate signal stats at tf=1m/3m, overlay none.

Usage:
  .venv/bin/python scripts/run_signal_lab_daysplit.py \
      --days 2026-09-09 2026-09-10 2026-09-11 [--strike-labels ATM ATM+1 ATM-1]

Research-only: gross premium points, no fills/costs. No orders.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "trading_agents_india" / "src"))

from trading_agents_india.chain_iv import load_iv_stats
from trading_agents_india.premium_tape import load_tape_bars
from trading_agents_india.session_clock import now_ist
from trading_agents_india.signal_lab import GATES, evaluate_combo

UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")
SIDES = ("ce", "pe")
TFS = (1, 3)


def day_character(day: str, und: str, side: str, bars) -> dict:
    rets = []
    for i in range(len(bars) - 16):
        e = bars[i + 1].open
        if e > 0:
            rets.append(100.0 * (bars[i + 16].close - e) / e)
    drift = round(sum(rets) / len(rets), 2) if rets else None
    session = (
        round(100.0 * (bars[-1].close - bars[0].open) / bars[0].open, 1)
        if bars and bars[0].open > 0
        else None
    )
    snaps = load_iv_stats(und, day=day)
    entropy = [s["iv_entropy"] for s in snaps if s.get("iv_entropy") is not None]
    tilt = [s["skew_tilt"] for s in snaps if s.get("skew_tilt") is not None]
    return {
        "drift_15m_pct": drift,
        "session_move_pct": session,
        "iv_entropy_mean": round(sum(entropy) / len(entropy), 6) if entropy else None,
        "skew_tilt_mean": round(sum(tilt) / len(tilt), 2) if tilt else None,
        "iv_snapshots": len(snaps),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", nargs="+", required=True)
    parser.add_argument("--strike-labels", nargs="+", default=["ATM"])
    args = parser.parse_args()

    all_rows = []
    for day in args.days:
        for und in UNDERLYINGS:
            for label in args.strike_labels:
                for side in SIDES:
                    bars = load_tape_bars(und, day=day, side=side, strike_label=label)
                    if len(bars) < 60:
                        continue
                    char = day_character(day, und, side, bars)
                    for tf in TFS:
                        for gate in GATES:
                            recs = evaluate_combo(
                                bars, day=day, underlying=und, side=side,
                                timeframe=tf, gate=gate, overlay="none",
                            )
                            rets = [r.fwd.get("ret_pct_15") for r in recs if r.fwd.get("ret_pct_15") is not None]
                            shells = [r.shell_pl_pct for r in recs if r.shell_pl_pct is not None]
                            if not recs:
                                continue
                            all_rows.append({
                                "day": day, "und": und, "side": side, "label": label,
                                "tf": tf, "gate": gate, "n": len(recs),
                                "avg_ret_pct_15m": round(sum(rets) / len(rets), 2) if rets else None,
                                "avg_shell_pl_pct": round(sum(shells) / len(shells), 2) if shells else None,
                                **char,
                            })

    print(f"{'day':<11} {'und':<9} {'side':<4} {'label':<5} {'tf':>2} {'gate':<10} "
          f"{'n':>3} {'ret%15':>7} {'shell%':>7} | {'drift%':>6} {'sess%':>6} {'entropy':>9} {'tilt':>5}")
    for r in all_rows:
        print(
            f"{r['day']:<11} {r['und']:<9} {r['side']:<4} {r['label']:<5} {r['tf']:>2} {r['gate']:<10} "
            f"{r['n']:>3} {str(r['avg_ret_pct_15m']):>7} {str(r['avg_shell_pl_pct']):>7} | "
            f"{str(r['drift_15m_pct']):>6} {str(r['session_move_pct']):>6} "
            f"{str(r['iv_entropy_mean']):>9} {str(r['skew_tilt_mean']):>5}"
        )

    # Aggregate: signal edge vs drift, grouped by side and day.
    print("\nEdge vs drift (signals avg minus unconditional drift), by day/side:")
    groups: dict[tuple[str, str], list] = {}
    for r in all_rows:
        if r["avg_ret_pct_15m"] is not None and r["drift_15m_pct"] is not None:
            groups.setdefault((r["day"], r["side"]), []).append(
                (r["avg_ret_pct_15m"] - r["drift_15m_pct"], r["n"])
            )
    for (day, side), vals in sorted(groups.items()):
        tot_n = sum(n for _, n in vals)
        wavg = sum(e * n for e, n in vals) / tot_n if tot_n else 0.0
        print(f"  {day} {side}: weighted edge {wavg:+.2f}% over {tot_n} signals")

    out_dir = Path("data/recon/signal_lab")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_ist().strftime("%Y-%m-%d_%H%M")
    out = out_dir / f"daysplit_{stamp}.json"
    out.write_text(json.dumps({"rows": all_rows}), encoding="utf-8")
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
