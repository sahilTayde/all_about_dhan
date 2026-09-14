"""CLI: python -m desk_ml fit|score. Cache only. No live Dhan. No orders."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from desk_ml.fit import fit_underlying, score_last
from desk_ml.persist import default_model_path, repo_root


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="desk_ml", description="ML-001 KMeans+IsolationForest overlay. NO_PROMOTE. No live orders.")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit", help="Fit on recon 1m INDEX+CE+PE cache")
    f.add_argument("--underlying", default="NIFTY")
    f.add_argument("--seed", type=int, default=14)
    f.add_argument("--no-persist", action="store_true")
    s = sub.add_parser("score", help="Score last aligned 1m triple after bar close")
    s.add_argument("--underlying", default="NIFTY")
    s.add_argument("--model", default="")
    return p


def _print(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    if args.cmd == "fit":
        report = fit_underlying(args.underlying, root=root, seed=args.seed, persist=not args.no_persist)
        public = {k: report[k] for k in (
            "ok", "status", "underlying", "n_rows", "n_feature_rows", "cluster_sizes",
            "centroids_orig", "supervised", "tape", "win_rate", "verdict", "promote",
            "production_params_written", "session_note", "path", "note",
        ) if k in report}
        _print(public)
        return 0 if report.get("ok") else 2
    path = default_model_path(args.underlying, root=root)
    if str(args.model or "").strip():
        path = Path(args.model)
    scored = score_last(args.underlying, root=root, model_path=path)
    _print(scored)
    return 0 if scored.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
