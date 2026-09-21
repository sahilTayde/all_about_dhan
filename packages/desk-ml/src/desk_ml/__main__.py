"""CLI: python -m desk_ml fit|score|mrr-fit|inventory|book-tune|replay-hold. Cache only. No live Dhan. No orders."""

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
from desk_ml.overlay import score_session
from desk_ml.paper_scalp import replay_paper_scalp, run_fix_first_drill, run_loop
from desk_ml.sod_exam import EXAM_DAYS_DEFAULT, run_sod_exam
from desk_ml.persist import default_model_path, repo_root
from desk_ml.replay import replay_hold


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="desk_ml",
        description="ML-001/002 overlay + parallel paper scalpers. replay-hold diagnostic. NO_PROMOTE. No live orders.",
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
    ov = sub.add_parser("overlay", help="Score NIFTY/BANKNIFTY/SENSEX paper overlay (dual-tape)")
    ov.add_argument("--source", default="dual-tape")
    ov.add_argument("--underlyings", default="NIFTY,BANKNIFTY,SENSEX")
    bt = sub.add_parser("book-tune", help="Inventory + ML-001 + ML-002 (max 3 MRR tweaks)")
    bt.add_argument("--calendar-days", type=int, default=21)
    bt.add_argument("--seed", type=int, default=14)
    bt.add_argument("--no-persist", action="store_true")
    rp = sub.add_parser(
        "replay-hold",
        help="Replay HOLD vs 15m ATM straddle bleed (diagnostic). Not a win rate.",
    )
    rp.add_argument("--underlying", default="NIFTY")
    rp.add_argument("--horizon-bars", type=int, default=15)
    rp.add_argument("--seed", type=int, default=14)
    ps = sub.add_parser(
        "paper-scalp",
        help="Parallel PAPER scalper books + monitoring JSON. Opt-in loop. No paper_ops. No live orders.",
    )
    ps.add_argument("--replay", action="store_true", help="Walk cache or dual-tape JSONL (default action)")
    ps.add_argument("--loop", action="store_true", help="Opt-in heartbeat loop; writes dashboard JSON")
    ps.add_argument("--source", default="cache", help="cache | dual-tape")
    ps.add_argument("--underlyings", default="NIFTY,BANKNIFTY,SENSEX")
    ps.add_argument("--tick-seconds", type=int, default=10)
    ps.add_argument(
        "--wipe-today",
        action="store_true",
        help="Archive today's paper jsonl + empty board. Does not delete warehouse/sqlite.",
    )
    ps.add_argument("--max-ticks", type=int, default=0, help="Loop only; 0 = until STOP flag")
    ps.add_argument("--max-closes", type=int, default=0, help="Stop replay after N closed paper trades (0 = all)")
    ps.add_argument(
        "--deny-signals",
        action="store_true",
        help="Force overlay SKIP (HOLD / meta-label). Default paper-scalp already denies clones.",
    )
    ps.add_argument("--no-write", action="store_true")
    ps.add_argument(
        "--live-session",
        action="store_true",
        help="Walk TODAY IST ticks only; keep OPEN rows; session P/L (default for dual-tape loop).",
    )
    ps.add_argument(
        "--session-date",
        default="",
        help="IST YYYY-MM-DD for --live-session (default: today IST). Replay 2026-09-16 tape without fabricating.",
    )
    ps.add_argument(
        "--sod-one-ticket",
        action="store_true",
        default=True,
        help="SOD product path (default on). No-op true; rooms are locked.",
    )
    ps.add_argument(
        "--sod-off",
        action="store_true",
        help="pytest A/B only: old parallel FILL_ELIGIBLE engine. Not the live path.",
    )
    ps.add_argument(
        "--observer-veto-fills",
        default=None,
        choices=["on", "off"],
        help="Observer veto on fills. Default on. --sod-off is the only old-engine switch.",
    )
    ff = sub.add_parser(
        "fix-first",
        help="Pre-open FIX-FIRST drill: write=false candle replay from 17 Sep. Skill track, not a wr.",
    )
    ff.add_argument("--since", default="2026-09-17", help="IST YYYY-MM-DD inclusive")
    ff.add_argument("--no-persist", action="store_true")
    ex = sub.add_parser(
        "sod-exam",
        help="06 honesty exam: lookahead slice + fill contract + why-spill. write=false. NO_PROMOTE.",
    )
    ex.add_argument("--days", default=",".join(EXAM_DAYS_DEFAULT), help="IST YYYY-MM-DD comma list")
    ex.add_argument("--underlyings", default="NIFTY")
    ex.add_argument("--source", default="dual-tape")
    ex.add_argument("--no-persist", action="store_true", help="Do not write recon/mock JSON")
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
    if args.cmd == "overlay":
        names = tuple(u.strip().upper() for u in str(args.underlyings).split(",") if u.strip())
        report = score_session(root=root, underlyings=names or ("NIFTY",), source=str(args.source))
        _print(report)
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
    if args.cmd == "replay-hold":
        report = replay_hold(
            args.underlying,
            root=root,
            horizon_bars=int(args.horizon_bars),
            seed=int(args.seed),
        )
        _print(report)
        return 0 if report.get("ok") else 2
    if args.cmd == "paper-scalp":
        names = tuple(u.strip().upper() for u in str(args.underlyings).split(",") if u.strip())
        if getattr(args, "wipe_today", False):
            from desk_ml.paper_scalp import wipe_today_paper_book

            _print(wipe_today_paper_book(root=root, ist_date=(str(args.session_date).strip() or None)))
            return 0
        if args.loop:
            report = run_loop(
                root=root,
                tick_seconds=int(args.tick_seconds),
                max_ticks=int(args.max_ticks),
                source=str(args.source),
                live_session=True,
            )
            public = {k: report[k] for k in report if k not in {"closed_trades"}}
            public["n_closed"] = len(report.get("closed_trades") or [])
            public["leaderboard"] = report.get("leaderboard")
            _print(public)
            return 0
        live = bool(args.live_session) or str(args.source).strip().lower() in {"dual-tape", "dual_tape"}
        veto = getattr(args, "observer_veto_fills", None)
        sod_off = bool(getattr(args, "sod_off", False))
        report = replay_paper_scalp(
            root=root,
            underlyings=names or ("NIFTY",),
            source=str(args.source),
            write=not bool(args.no_write),
            max_closes=int(args.max_closes or 0),
            deny_model_signals=True,
            live_session=live,
            session_ist_date=(str(args.session_date).strip() or None),
            sod_one_ticket=False if sod_off else True,
            picker_majority=False if sod_off else True,
            observer_veto_fills=(None if veto is None else veto == "on"),
        )
        public = {
            k: report.get(k)
            for k in (
                "ok",
                "job",
                "as_of_ist",
                "gate",
                "promote",
                "win_rate",
                "win_rate_pct",
                "win_rate_net_pct",
                "win_rate_gross_pct",
                "n_wins",
                "n_losses",
                "starting_capital_inr_per_book",
                "capital_plan",
                "starting_desk_inr",
                "source",
                "independent_books",
                "models",
                "leaderboard",
                "inventory",
                "heartbeat",
                "honesty",
                "scalper_exits",
                "execution",
            )
        }
        public["n_closed"] = len(report.get("closed_trades") or [])
        public["n_open"] = len(report.get("open_trades") or [])
        public["overall_pnl_inr"] = report.get("overall_pnl_inr")
        public["overall_gross_pnl_inr"] = report.get("overall_gross_pnl_inr")
        public["overall_charges_inr"] = report.get("overall_charges_inr")
        public["book_rank"] = report.get("book_rank")
        public["today"] = report.get("today")
        public["index_notes"] = report.get("index_notes")
        public["money_lost_inr"] = report.get("money_lost_inr")
        public["live_session"] = report.get("live_session")
        public["session_ist_date"] = report.get("session_ist_date")
        public["n_skip_sideways"] = report.get("n_skip_sideways")
        public["n_sideways_bars"] = report.get("n_sideways_bars")
        public["n_sl_hit"] = report.get("n_sl_hit")
        public["last_index_regime"] = report.get("last_index_regime")
        public["data_gaps"] = (report.get("inventory") or {}).get("data_gaps")
        public["steps_status"] = {
            u: (s or {}).get("status") for u, s in (report.get("steps") or {}).items()
        }
        _print(public)
        return 0 if report.get("ok") else 2
    if args.cmd == "fix-first":
        report = run_fix_first_drill(
            root=root,
            since=str(args.since).strip() or "2026-09-17",
            persist=not bool(args.no_persist),
        )
        public = {k: report.get(k) for k in report if k != "days"}
        public["n_days"] = len(report.get("days") or [])
        public["days"] = [
            {
                "ist_date": d.get("ist_date"),
                "n_filled_dealer": d.get("n_filled_dealer"),
                "n_target": d.get("n_target"),
                "n_stall": d.get("n_stall"),
                "n_against": d.get("n_against"),
                "n_unwind": d.get("n_unwind"),
                "win_rate_net_pct": d.get("win_rate_net_pct"),
                "net_pnl_inr": d.get("net_pnl_inr"),
                "lessons": d.get("lessons"),
                "fills_by_kind": d.get("fills_by_kind"),
                "exits_by_kind": d.get("exits_by_kind"),
                "exits_by_open_kind": d.get("exits_by_open_kind"),
                "n_stall_trending_open": d.get("n_stall_trending_open"),
                "tape_kinds": d.get("tape_kinds"),
                "signal_desk": d.get("signal_desk"),
            }
            for d in (report.get("days") or [])
        ]
        public["day_over_day"] = report.get("day_over_day")
        public["watch"] = report.get("watch")
        public["improve_next"] = report.get("improve_next")
        _print(public)
        return 0 if report.get("ok") else 2
    if args.cmd == "sod-exam":
        days = [d.strip() for d in str(args.days).split(",") if d.strip()]
        names = tuple(u.strip().upper() for u in str(args.underlyings).split(",") if u.strip())
        report = run_sod_exam(
            days=days or list(EXAM_DAYS_DEFAULT),
            root=root,
            underlyings=names or ("NIFTY",),
            source=str(args.source),
            persist=not bool(args.no_persist),
        )
        public = {
            k: report.get(k)
            for k in (
                "ok",
                "job",
                "as_of_ist",
                "gate",
                "promote",
                "orders",
                "win_rate",
                "overall_honesty",
                "headline",
                "stories",
                "watch_next",
                "contract",
                "how_to_read",
                "path",
                "mock_path",
                "cli",
                "note",
                "one_day_is_not_retune",
            )
            if k in report
        }
        public["days"] = [
            {
                "day": d.get("day"),
                "honesty": d.get("honesty"),
                "session_kind": d.get("session_kind"),
                "n_triples": d.get("n_triples"),
                "n_sod_closed": d.get("n_sod_closed"),
                "n_peeked_slices": d.get("n_peeked_slices"),
                "n_fill_contract_fail": d.get("n_fill_contract_fail"),
                "story": d.get("story"),
                "improve": d.get("improve"),
                "tape_note": d.get("tape_note"),
            }
            for d in (report.get("days") or [])
        ]
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
