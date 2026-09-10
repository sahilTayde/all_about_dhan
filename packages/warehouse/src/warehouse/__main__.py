"""CLI: python -m warehouse

Never prints secrets. No live Dhan. Does not open transcripts.sqlite.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from warehouse.feasibility import evaluate_long_premium
from warehouse.paths import default_db
from warehouse.store import Warehouse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="warehouse",
        description="DATA-001 append-only paper warehouse. No live orders.",
    )
    parser.add_argument("--db", default="", help="SQLite path (default data/knowledge/warehouse.sqlite)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create schema (WAL)")
    sub.add_parser("status", help="Row counts; never prints secrets")

    p_chk = sub.add_parser("check-ticket", help="DEALER-001 long-premium feasibility (no LLM)")
    p_chk.add_argument("--entry", type=float, required=True)
    p_chk.add_argument("--stop", type=float, required=True)
    p_chk.add_argument("--target", type=float, required=True)
    p_chk.add_argument("--stage", default="WATCH")
    p_chk.add_argument("--tape-age-sec", type=float, default=None)
    p_chk.add_argument("--typical-range", type=float, default=None)

    p_in = sub.add_parser(
        "ingest",
        help="One-shot INDEX 1m + ATM/PCR into warehouse (no poll loop, no orders)",
    )
    p_in.add_argument(
        "--live",
        action="store_true",
        help="Use Dhan gather hooks (tokens required). Default is fixture/DI path.",
    )
    p_in.add_argument(
        "--offline",
        action="store_true",
        help="Force fixtures / DATA_INSUFFICIENT (no Dhan HTTP)",
    )

    p_c = sub.add_parser(
        "candles",
        help="One-shot 1m/5m/15m/60m/1d pull + 3m/1w resample (no poll loop)",
    )
    p_c.add_argument("--live", action="store_true", help="Call Dhan charts")
    p_c.add_argument("--offline", action="store_true")

    p_b = sub.add_parser("bars", help="Read stored/resampled candles for analysis")
    p_b.add_argument("--symbol", default="NIFTY")
    p_b.add_argument("--tf", default="3m", help="1m|3m|5m|15m|60m|1d|1w")
    p_b.add_argument("--limit", type=int, default=8)

    p_d = sub.add_parser(
        "desk-book",
        help="One-shot full chain strikes + ATM CE/PE levels + constituent LTPs (no loop)",
    )
    p_d.add_argument("--live", action="store_true")
    p_d.add_argument("--offline", action="store_true")
    return parser


def _wh(args: argparse.Namespace) -> Warehouse:
    path = Path(args.db).resolve() if str(args.db or "").strip() else default_db()
    return Warehouse(path)


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "init":
        print(json.dumps(_wh(args).init(), indent=2))
        return 0
    if args.cmd == "status":
        print(json.dumps(_wh(args).status(), indent=2))
        return 0
    if args.cmd == "check-ticket":
        decision = evaluate_long_premium(
            entry=args.entry,
            stop=args.stop,
            target=args.target,
            stage=args.stage,
            tape_age_sec=args.tape_age_sec,
            typical_premium_range=args.typical_range,
        )
        print(json.dumps(decision.to_dict(), indent=2))
        return 0 if decision.ok or decision.action == "HOLD" else 2
    if args.cmd == "ingest":
        from warehouse.ingest import ingest_once

        live = bool(args.live) and not bool(args.offline)
        print(json.dumps(ingest_once(live=live, warehouse=_wh(args)), indent=2, default=str))
        return 0
    if args.cmd == "candles":
        from warehouse.candles import sync_candles

        live = bool(args.live) and not bool(args.offline)
        print(json.dumps(sync_candles(live=live, warehouse=_wh(args)), indent=2, default=str))
        return 0
    if args.cmd == "bars":
        from warehouse.candles import list_bars

        print(
            json.dumps(
                list_bars(args.symbol, args.tf, limit=args.limit, warehouse=_wh(args)),
                indent=2,
                default=str,
            )
        )
        return 0
    if args.cmd == "desk-book":
        from warehouse.desk_book import sync_desk_book

        live = bool(args.live) and not bool(args.offline)
        print(json.dumps(sync_desk_book(live=live, warehouse=_wh(args)), indent=2, default=str))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
