#!/usr/bin/env python3
"""Paper cost ablation: legacy vs realistic P&L per day for a dual-tape folder (spec §10.3).

Each step turns on one realistic component, cumulatively, on the same flag-off replay:

    0 legacy                today's numbers (must match the recorded legacy totals exactly)
    1 +slippage             spread/slippage per side; stops/targets still from the signal price
    2 +resting target       TARGET exits book the target level
    3 +stale-quote guard    exits wait for a fresh held-strike print; FLATTEN_STALE_QUOTE at 15:20
    4 +exchange fees        SENSEX/BANKEX at the BSE rate, NSE at the Mar-2026 rate
    5 +tick/trade-through   working limits tick-floored, fill only on a trade-through (= realistic)

Usage (offline; nothing is written under the data root; no broker is called):

    python scripts/cost_ablation.py --root <data root with data/recon/paper_watch/DUAL-TAPE>
    python scripts/cost_ablation.py --tapes <root>/data/recon/paper_watch/DUAL-TAPE --since 2026-09-17
    python scripts/cost_ablation.py --tapes ./tapes --founder-start NIFTY,BANKNIFTY,SENSEX --quick

`--tapes` pointing inside a data root uses that root (params, founder file, lot cache). Any other
folder is replayed from a scratch root (default params; founder START for --underlyings).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Optional, Sequence
from unittest.mock import patch

DEFAULT_LOTS = {"NIFTY": 65, "BANKNIFTY": 30, "SENSEX": 20}  # optidx_lot_cache.json on the box (cost_audit.md)
OFF = {"target_fill": "market_at_poll", "exit_quote_max_age_s": None, "exchange_fees": "nse_flat",
       "limit_fill": "touch"}
COMPONENTS = (("1 +slippage", None), ("2 +resting target", "target_fill"), ("3 +stale guard", "exit_quote_max_age_s"),
              ("4 +exchange fees", "exchange_fees"), ("5 +tick/trade-through", "limit_fill"))


def steps(quick: bool) -> list[tuple[str, str, dict[str, Any]]]:
    from desk_ml import costs

    full = costs.load_config()
    out, ov = [("0 legacy", costs.LEGACY, {})], dict(OFF)
    for name, key in COMPONENTS:
        if key is not None:
            ov = {**ov, key: full[key]}
        out.append((name, costs.REALISTIC, dict(ov)))
    return [out[0], out[-1]] if quick else out


def _kw(items: Sequence[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items:
        key, _, raw = item.partition("=")
        try:
            out[key] = json.loads(raw)
        except json.JSONDecodeError:
            out[key] = raw
    return out


def resolve_root(args: argparse.Namespace, stack: ExitStack) -> tuple[Path, bool]:
    """(root, scratch). A folder that is not <root>/data/recon/paper_watch/DUAL-TAPE gets a scratch root."""
    if args.root:
        return Path(args.root).resolve(), False
    tapes = Path(args.tapes).resolve()
    if not tapes.is_dir():
        raise SystemExit(f"--tapes {tapes} is not a folder")
    if tapes.name == "DUAL-TAPE" and [tapes.parents[i].name for i in range(3)] == ["paper_watch", "recon", "data"]:
        return tapes.parents[3], False
    root = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="cost_ablation_")))
    dest = root / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    dest.mkdir(parents=True)
    for f in sorted(tapes.glob("*.jsonl")):
        (dest / f.name).symlink_to(f)
    if args.params:
        shutil.copy(args.params, root / "data" / "recon" / "ml_paper_session_params.json")
    return root, True


def pin_inputs(data_root: Path, founder: Optional[list[str]], lots: dict[str, int]) -> list[str]:
    """In-process only: founder START list and lot sizes. Never writes a founder file, never fetches lots."""
    import desk_ml.founder_session as fs
    import desk_ml.paper_scalp as ps
    from desk_ml.paper_lots import _from_disk

    notes = []
    if founder is not None:
        fs.load_founder_book = lambda root=None: fs._payload(list(founder), source="cost_ablation_in_process")
        notes.append(f"founder START (in-process): {','.join(founder) or 'none'}")

    def lot(und: str, root: Optional[Path] = None) -> tuple[Optional[int], str]:
        disk = _from_disk(Path(root) if root else data_root, und)
        return disk if disk is not None else (lots[und.upper()], "cost_ablation_default")

    ps.resolve_lot_size = lot  # replaces the instrument-master fetch fallback: no network
    missing = [u for u in lots if _from_disk(data_root, u) is None]
    if missing:
        notes.append(f"lot sizes not in data/recon/optidx_lot_cache.json, using {[(u, lots[u]) for u in missing]}")
    return notes


def run_day(root: Path, day: str, args: argparse.Namespace, plan: list, kw: dict[str, Any]) -> dict[str, Any]:
    from desk_ml import costs
    from desk_ml.paper_scalp import replay_paper_scalp

    out: dict[str, Any] = {}
    for name, model, ov in plan:
        with costs.overrides(**ov):
            board = replay_paper_scalp(
                root=root, underlyings=tuple(args.underlyings), source="dual-tape", write=False,
                live_session=not args.no_live_session, session_ist_date=day, use_event_bus=False,
                cost_model=model, **kw,
            )
        rows = [r for r in board.get("closed_trades") or [] if r.get("filled")]
        out[name] = {
            "n_trades": len(rows),
            "net": round(sum(float(r.get("realized_pnl_inr") or 0.0) for r in rows), 2),
            "gross": round(sum(float(r.get("gross_pnl_inr") or 0.0) for r in rows), 2),
            "charges": round(sum(float(r.get("charges_inr") or 0.0) for r in rows), 2),
            "slippage": round(sum(float(r.get("slippage_inr") or 0.0) for r in rows), 2),
            "by_index": {u: round(sum(float(r["realized_pnl_inr"] or 0.0) for r in rows if r["underlying"] == u), 2)
                         for u in args.underlyings},
            "decisions": sorted([r["trade_id"], int(r["closed_ts"]), str(r["exit_reason"])] for r in rows),
            "n_stale_alerts": int((board.get("cost_model") or {}).get("n_alerts") or 0),
        }
    return out


def _money(x: float) -> str:
    return f"{x:+,.2f}"


def report(results: dict[str, dict[str, Any]], plan: list, notes: list[str]) -> str:
    names = [p[0] for p in plan]
    lines = [*(f"> {n}" for n in notes), "", "| day | " + " | ".join(names) + " |",
             "|---|" + "---|" * len(names)]
    tot = {n: {"n_trades": 0, "net": 0.0, "gross": 0.0, "charges": 0.0, "slippage": 0.0, "stale": 0,
               "by_index": {}} for n in names}
    for day, steps_out in results.items():
        cells = []
        for n in names:
            s = steps_out[n]
            cells.append(f"{s['n_trades']} / {_money(s['net'])}")
            t = tot[n]
            for k in ("n_trades", "net", "gross", "charges", "slippage"):
                t[k] = round(t[k] + s[k], 2) if k != "n_trades" else t[k] + s[k]
            t["stale"] += s["n_stale_alerts"]
            for u, v in s["by_index"].items():
                t["by_index"][u] = round(t["by_index"].get(u, 0.0) + v, 2)
        lines.append(f"| {day} | " + " | ".join(cells) + " |")
    lines.append("| **TOTAL** | " + " | ".join(f"**{tot[n]['n_trades']} / {_money(tot[n]['net'])}**" for n in names) + " |")
    lines += ["", "| step | trades | net | Δnet vs previous | gross | charges | slippage | stale alerts | "
              "decision changes vs previous | net by index |", "|---|---|---|---|---|---|---|---|---|---|"]
    prev = None
    for n in names:
        t = tot[n]
        changed = "-"
        if prev is not None:
            diff = sum(
                len({tuple(x) for x in results[d][n]["decisions"]} ^ {tuple(x) for x in results[d][prev]["decisions"]})
                for d in results
            )
            changed = str(diff)
        delta = "-" if prev is None else _money(t["net"] - tot[prev]["net"])
        by_idx = ", ".join(f"{u} {_money(v)}" for u, v in t["by_index"].items())
        lines.append(f"| {n} | {t['n_trades']} | {_money(t['net'])} | {delta} | {_money(t['gross'])} | "
                     f"{t['charges']:,.2f} | {t['slippage']:,.2f} | {t['stale']} | {changed} | {by_idx} |")
        prev = n
    lines.append("")
    lines.append("decision changes = trades whose (trade_id, closed_ts, exit_reason) differ, counted on both sides.")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scripts/cost_ablation.py", description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--root", type=Path, help="data root holding data/recon/paper_watch/DUAL-TAPE")
    src.add_argument("--tapes", type=Path, help="folder of <YYYY-MM-DD>.jsonl dual-tape files")
    ap.add_argument("--days", nargs="*", help="explicit IST dates (default: every tape day in --since..--until)")
    ap.add_argument("--since", default="2026-09-17")
    ap.add_argument("--until", default="2026-09-25")
    ap.add_argument("--underlyings", nargs="*", default=["NIFTY"])
    ap.add_argument("--founder-start", help="comma list START in-process (e.g. NIFTY,BANKNIFTY,SENSEX); "
                                            "default: the root's founder file, or --underlyings on a scratch root")
    ap.add_argument("--params", type=Path, help="scratch root only: copy this ml_paper_session_params.json in")
    ap.add_argument("--lot-sizes", default=",".join(f"{k}={v}" for k, v in DEFAULT_LOTS.items()),
                    help="used only when the root has no lot cache (never fetched)")
    ap.add_argument("--no-live-session", action="store_true", help="historical replay instead of live-session params")
    ap.add_argument("--kw", action="append", default=[], metavar="KEY=JSON", help="extra replay_paper_scalp kwarg")
    ap.add_argument("--quick", action="store_true", help="legacy vs full realistic only")
    ap.add_argument("--out", type=Path, help="also write the markdown table here")
    ap.add_argument("--json", type=Path, help="also write per-day, per-step results as JSON")
    args = ap.parse_args(argv)
    args.underlyings = [u.upper() for u in args.underlyings]

    from desk_ml.paper_scalp import list_fix_first_days

    with ExitStack() as stack:
        # Shadow rows (desk_ml.shadow_log) append under the replay root even with write=False.
        stack.enter_context(patch.dict(os.environ, {"SHADOW_LOG": "0"}))
        root, scratch = resolve_root(args, stack)
        founder = [u.strip().upper() for u in args.founder_start.split(",") if u.strip()] if args.founder_start \
            else (list(args.underlyings) if scratch else None)
        lots = {**DEFAULT_LOTS, **{k.upper(): int(v) for k, v in (p.split("=") for p in args.lot_sizes.split(",") if p)}}
        notes = [f"root: {root}{' (scratch)' if scratch else ''}", *pin_inputs(root, founder, lots)]
        days = args.days or [d for d in list_fix_first_days(root=root, since=args.since) if d <= args.until]
        if not days:
            print(f"no dual-tape days under {root}/data/recon/paper_watch/DUAL-TAPE for {args.since}..{args.until}")
            return 1
        plan = steps(args.quick)
        kw = _kw(args.kw)
        results = {}
        for day in days:
            results[day] = run_day(root, day, args, plan, kw)
            print(f"{day}: " + "  ".join(f"[{n}] {s['n_trades']} / {_money(s['net'])}" for n, s in results[day].items()),
                  file=sys.stderr)
    text = report(results, plan, notes)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
