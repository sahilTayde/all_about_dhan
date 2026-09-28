"""CLI: one command per experiment. Paper/replay only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from exitlab.plans import library, sweep_specs
from exitlab.playbook import (
    PLAYBOOK_RELATIVE,
    load_playbook_yaml,
    playbook_enabled,
    playbook_to_exit_plan_mapping,
)
from exitlab.research import measure_history, measure_live_tapes, run_research


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Exit lab (paper/replay only). No Dhan.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_m = sub.add_parser("measure", help="Market measurements from attached data")
    p_m.add_argument("--data", type=Path, required=True)
    p_m.add_argument("--out", type=Path, required=True)
    p_m.add_argument("--source", choices=("live", "history", "both"), default="both")

    p_r = sub.add_parser("research", help="Full grid: entries, plans, sweeps, stress, tables")
    p_r.add_argument("--data", type=Path, required=True)
    p_r.add_argument("--out", type=Path, required=True)
    p_r.add_argument("--seed", type=int, default=7)
    p_r.add_argument("--max-hist-days", type=int, default=40)
    p_r.add_argument("--extra-seeds", default="11,19")
    p_r.add_argument("--reuse-entries", type=Path, default=None)

    sub.add_parser("prove-lookahead", help="Honest clock passes; injected future read raises")

    p_p = sub.add_parser("playbook", help="Show opt-in playbook (OFF unless enabled)")
    p_p.add_argument("--path", type=Path, default=PLAYBOOK_RELATIVE)
    p_p.add_argument("--env-flag", default="")

    sub.add_parser("list-plans", help="Named plans and sweep count")

    args = ap.parse_args(argv)
    if args.cmd == "measure":
        args.out.mkdir(parents=True, exist_ok=True)
        if args.source in {"live", "both"}:
            payload = measure_live_tapes(args.data)
            (args.out / "measure_live.json").write_text(
                json.dumps(payload, indent=2, default=str) + "\n"
            )
            n_sess = payload.get("n_sessions_labelled")
            print(f"wrote {args.out / 'measure_live.json'} sessions={n_sess}")
        if args.source in {"history", "both"}:
            payload = measure_history(args.data)
            (args.out / "measure_history.json").write_text(
                json.dumps(payload, indent=2, default=str) + "\n"
            )
            print(f"wrote {args.out / 'measure_history.json'} ok={payload.get('ok', True)}")
        return 0
    if args.cmd == "research":
        extra = tuple(int(x) for x in str(args.extra_seeds).split(",") if x.strip())
        tables = run_research(
            data=args.data,
            out=args.out,
            seed=args.seed,
            max_hist_days=args.max_hist_days,
            extra_seeds=extra,
            reuse_entries=args.reuse_entries,
        )
        print(
            json.dumps(
                {
                    "out": str(args.out),
                    "n_variants_tested": tables.get("n_variants_tested"),
                    "n_entries_live": tables.get("n_entries_live"),
                    "n_entries_hist": tables.get("n_entries_hist"),
                    "n_trade_results": tables.get("n_trade_results"),
                    "sweep_winner": tables.get("sweep_winner"),
                },
                indent=2,
            )
        )
        return 0
    if args.cmd == "playbook":
        raw = load_playbook_yaml(args.path)
        on = playbook_enabled(raw, env_flag=args.env_flag)
        print(
            json.dumps(
                {
                    "enabled": on,
                    "mapping": playbook_to_exit_plan_mapping(raw) if on else None,
                    "raw_enabled": raw.get("enabled"),
                },
                indent=2,
            )
        )
        return 0
    if args.cmd == "prove-lookahead":
        from datetime import datetime

        from exitlab.clock import IST, LookAheadError, ReplayClock

        clock = ReplayClock(datetime(2026, 9, 17, 10, 5, tzinfo=IST))
        clock.visible(datetime(2026, 9, 17, 10, 5, tzinfo=IST), label="honest")
        print("HONEST_OK")
        try:
            clock.visible(datetime(2026, 9, 17, 15, 20, tzinfo=IST), label="injected_future")
        except LookAheadError as exc:
            print(f"INJECT_RAISED {exc}")
            return 0
        print("INJECT_DID_NOT_RAISE")
        return 1
    if args.cmd == "list-plans":
        print(
            json.dumps(
                {"library": sorted(library()), "n_sweep_specs": len(sweep_specs())}, indent=2
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
