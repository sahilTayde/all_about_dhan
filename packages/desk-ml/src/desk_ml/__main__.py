"""CLI: python -m desk_ml fit|score|mrr-fit|inventory|book-tune. Cache only. No live Dhan. No orders."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from desk_ml.book_tune import run_book_tune
from desk_ml.fit import fit_underlying, score_last
from desk_ml.inventory import inventory_recon
from desk_ml.mrr import MRR_WINDOWS, mrr_fit_underlying, score_mrr_last
from desk_ml.persist import default_model_path, repo_root


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="desk_ml",
        description="ML-001 KMeans+IF and ML-002 MRR/OU overlay. NO_PROMOTE. No live orders.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit", help="Fit ML-001 on recon 1m INDEX+CE+PE cache")
    f.add_argument("--underlying", default="NIFTY")
    f.add_argument("--seed", type=int, default=14)
    f.add_argument("--embargo-bars", type=int, default=5)
    f.add_argument("--no-persist", action="store_true")
    s = sub.add_parser("score", help="Score last aligned 1m triple after bar close")
    s.add_argument("--underlying", default="NIFTY")
    s.add_argument("--model", default="")
    s.add_argument("--source", default="cache", help="cache | dual-tape")
    s.add_argument("--model-id", default="ML-001", help="ML-001 | ML-002 | both")
    m = sub.add_parser("mrr-fit", help="Fit ML-002 OU residual + VWMA windows 40/60/90")
    m.add_argument("--underlying", default="NIFTY")
    m.add_argument("--windows", default="40,60,90")
    m.add_argument("--no-persist", action="store_true")
    inv = sub.add_parser("inventory", help="INDEX 1m / premium_tape / OPTIDX last ~21d")
    inv.add_argument("--calendar-days", type=int, default=21)
    bt = sub.add_parser("book-tune", help="Inventory + ML-001 + ML-002 (max 3 MRR tweaks)")
    bt.add_argument("--calendar-days", type=int, default=21)
    bt.add_argument("--seed", type=int, default=14)
    bt.add_argument("--no-persist", action="store_true")
    return p


def _print(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def _windows(raw: str) -> list[int]:
    parts = [int(p.strip()) for p in str(raw).split(",") if p.strip()]
    return (parts or list(MRR_WINDOWS))[:3]


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    if args.cmd == "fit":
        report = fit_underlying(
            args.underlying,
            root=root,
            seed=args.seed,
            persist=not args.no_persist,
            embargo_bars=int(args.embargo_bars),
        )
        public = {k: report[k] for k in (
            "ok", "status", "underlying", "n_rows", "n_feature_rows", "cluster_sizes",
            "centroids_orig", "supervised", "tape", "embargo", "win_rate", "verdict", "promote",
            "production_params_written", "session_note", "path", "note",
        ) if k in report}
        _print(public)
        return 0 if report.get("ok") else 2
    if args.cmd == "mrr-fit":
        report = mrr_fit_underlying(
            args.underlying,
            root=root,
            windows=_windows(args.windows),
            persist=not args.no_persist,
        )
        public = {k: report[k] for k in (
            "ok", "status", "model_id", "underlying", "k_ce", "k_pe", "windows_tried",
            "tweaks", "preferred", "n_feature_rows", "win_rate", "verdict", "promote",
            "production_params_written", "gate", "path", "note", "tape",
        ) if k in report}
        _print(public)
        return 0 if report.get("ok") else 2
    if args.cmd == "inventory":
        _print(inventory_recon(root=root, calendar_days=args.calendar_days))
        return 0
    if args.cmd == "book-tune":
        report = run_book_tune(
            root=root,
            calendar_days=args.calendar_days,
            seed=args.seed,
            persist=not args.no_persist,
        )
        public = {k: report[k] for k in report if k != "inventory"}
        public["inventory_gaps"] = (report.get("inventory") or {}).get("data_gaps")
        public["inventory_joins"] = (report.get("inventory") or {}).get("joins")
        _print(public)
        return 0 if report.get("ok") else 2
    path = default_model_path(args.underlying, root=root)
    if str(args.model or "").strip():
        path = Path(args.model)
    mid = str(args.model_id or "ML-001").upper()
    src = str(args.source or "cache")
    out: dict[str, Any] = {"production_params_written": False, "promote": False, "execution": "refused"}
    ok = True
    if mid in {"ML-001", "BOTH", "ALL"}:
        scored = score_last(args.underlying, root=root, model_path=path, source=src)
        out["ml001"] = scored
        ok = ok and bool(scored.get("ok"))
        if mid == "ML-001":
            _print(scored)
            return 0 if scored.get("ok") else 2
    if mid in {"ML-002", "BOTH", "ALL"}:
        mrr = score_mrr_last(args.underlying, root=root, source=src)
        out["ml002"] = mrr
        ok = ok and bool(mrr.get("ok"))
        if mid == "ML-002":
            _print(mrr)
            return 0 if mrr.get("ok") else 2
    follow = bool((out.get("ml001") or {}).get("follow_gap")) or bool((out.get("ml002") or {}).get("follow_gap"))
    out["follow_gap"] = follow
    out["session_action"] = "HOLD" if follow else "WATCH_ONLY"
    out["ok"] = ok
    _print(out)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
