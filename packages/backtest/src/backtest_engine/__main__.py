"""CLI: python -m backtest_engine books --live --years 5"""

from __future__ import annotations

import argparse
import json
import sys

from dhan_client.client import DhanClient

from backtest_engine.run_books import run_books
from backtest_engine.run_index_5m import run_default
from backtest_engine.run_option import run_option_premium
from backtest_engine.run_project import run_project_mixes
from backtest_engine.run_club import run_club
from backtest_engine.run_honest import run_honest
from backtest_engine.run_scan import run_scan
from backtest_engine.run_sltp import run_sltp

_CF_GONE = frozenset(
    {
        "cf-fabio",
        "cf-marco-mayne",
        "cf-marci-tori",
        "cf-tg-kane",
        "cf-umar-forest",
        "cf-carmine-jadecap",
        "cf-usman-brando",
        "cf-andrea-omor",
        "okala-in",
        "okala-signal",
        "cf-overnight",
        "cf-india",
        "cf-signal",
    }
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Paper backtests. No orders. Proxy points ≠ option P/L."
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--years", type=float, default=5.0)
    parser.add_argument("--interval", type=int, default=1, choices=(1, 5, 15, 25, 60))
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("books", help="Large-chunk STRAT/MIX books + OOS ratings.")
    sub.add_parser("index-5m", help="Legacy 5m INDEX bar-count stub.")
    sub.add_parser("option", help="Rolling OPTIDX premium vs INDEX 3m leans.")
    sub.add_parser("project", help="PROJECT_MIX MIX-MTF-TREND / MIX-CONFIRM-5M on NIFTY+SENSEX.")
    sub.add_parser(
        "scan",
        help="WEB/PATTERN + ML MIX; drop 09:00-09:30 and 15:00-15:30 IST.",
    )
    sub.add_parser(
        "club",
        help="2y club of WEAK books + annexure RSI/SMA/MACD + nested param grid.",
    )
    sub.add_parser(
        "honest",
        help="Rescore frozen club books after hypothesis costs + expiry strip. No retune.",
    )
    sub.add_parser(
        "sltp",
        help="Named SL/TP overlays (ATR+R2, ST flip) on NIFTY INDEX 3m. No promote.",
    )
    sub.add_parser(
        "cf-fabio",
        help="Chart Fanatics Fabio MIX-CF-* OHLC proxies on NIFTY. OF PARKED. No promote.",
    )
    sub.add_parser(
        "cf-marco-mayne",
        help="Chart Fanatics Marco+Mayne MIX-CF-* OHLC proxies on NIFTY. ASR. No promote.",
    )
    sub.add_parser(
        "cf-marci-tori",
        help="Chart Fanatics Marci+Tori MIX-CF-* OHLC proxies on NIFTY. ASR. No promote.",
    )
    sub.add_parser(
        "cf-tg-kane",
        help="Chart Fanatics TG+Kane MIX-CF-* OHLC proxies on NIFTY. ASR. No promote.",
    )
    sub.add_parser(
        "cf-umar-forest",
        help="Chart Fanatics Umar+Forest MIX-CF-* OHLC proxies on NIFTY. ASR. No promote.",
    )
    sub.add_parser(
        "cf-carmine-jadecap",
        help="Chart Fanatics Carmine+Jadecap MIX-CF-* OHLC proxies on NIFTY. ASR. No promote.",
    )
    sub.add_parser(
        "cf-usman-brando",
        help="Chart Fanatics Usman+Brando MIX-CF-* OHLC proxies on NIFTY. ASR. No promote.",
    )
    sub.add_parser(
        "cf-andrea-omor",
        help="Chart Fanatics Andrea+Omor MIX-CF-* OHLC proxies on NIFTY. ASR. No promote.",
    )
    p_okala = sub.add_parser(
        "okala-in",
        help="Okala India adaptation MIX-CF-OKALA-IN-* grid (NIFTY/BN × TF × regime × magnets). NO_PROMOTE.",
    )
    p_okala.add_argument(
        "--grid-years",
        type=float,
        default=2.0,
        help="Lookback years for TF>1m (cache trim).",
    )
    p_okala.add_argument(
        "--years-1m",
        type=float,
        default=0.5,
        help="Shorter lookback for 1m TF (runtime cap).",
    )
    p_okala.add_argument("--magnet-seed", type=int, default=20260907)
    p_sig = sub.add_parser(
        "okala-signal",
        help="One-shot dry-run: detect_okala_signal → CE/PE + premium levels JSON. PAPER only.",
    )
    p_sig.add_argument(
        "--underlying",
        default="NIFTY",
        choices=("NIFTY", "BANKNIFTY", "SENSEX"),
    )
    p_sig.add_argument("--option-ltp", type=float, default=100.0, help="Mock premium LTP")
    p_sig.add_argument("--strike", type=int, default=0, help="Optional mock strike (0=omit)")
    p_cf = sub.add_parser(
        "cf-overnight",
        help="CF India overnight permutations (structure families + Okala rollup). NO_PROMOTE.",
    )
    p_cf.add_argument("--grid-years", type=float, default=2.0)
    p_cf.add_argument("--years-1m", type=float, default=0.5)
    p_cfi = sub.add_parser(
        "cf-india",
        help="Lightweight CF India family probe (cf_india_proxy sibling; does not rewrite okala_in_proxy). NO_PROMOTE.",
    )
    p_cfi.add_argument("--family", default="YUSH", help="Guest slug e.g. YUSH / MARCO-DAV / FABIO")
    p_cfi.add_argument("--underlying", default="NIFTY", choices=("NIFTY", "BANKNIFTY", "SENSEX"))
    p_cf_sig = sub.add_parser(
        "cf-signal",
        help="Dry-run CF plugin registry detect_cf_signal → CE/PE + premium. PAPER only.",
    )
    p_cf_sig.add_argument(
        "--underlying",
        default="NIFTY",
        choices=("NIFTY", "BANKNIFTY", "SENSEX"),
    )
    p_cf_sig.add_argument("--option-ltp", type=float, default=100.0)
    args = parser.parse_args(argv)
    dry: bool | None
    if args.live:
        dry = False
    elif args.dry_run:
        dry = True
    else:
        dry = None
    cmd = args.cmd or "books"
    if cmd in _CF_GONE:
        print(
            "removed: Chart Fanatics / Okala CLI (DhanHQ-only reset 2026-09-09)",
            file=sys.stderr,
        )
        return 2
    if cmd == "cf-signal":
        from backtest_engine.cf_paper_registry import detect_cf_signal, registry_meta
        from backtest_engine.indicators import Bar

        base_ts = 1704155400
        bars = [
            Bar(
                ts=base_ts + i * 60,
                open=24000 + (i % 5),
                high=24010 + (i % 5),
                low=23990 + (i % 5),
                close=24000 + (i % 5),
                volume=1.0,
            )
            for i in range(100)
        ]
        sig = detect_cf_signal(
            str(args.underlying).upper(),
            bars,
            option_ltp=float(args.option_ltp),
            premium_meta={"source": "mock_dry_run"},
            session_kind="NEWS_DAY",
            veto_reasons=["BIG_NEWS dry-run"],
        )
        print(
            json.dumps(
                {
                    "orders": "refused",
                    "paper_only": True,
                    "research_ready_for_programming": False,
                    "registry": registry_meta(),
                    "signal": sig,
                },
                indent=2,
                default=str,
            )
        )
        return 0
    if cmd == "cf-overnight":
        report = run_cf_overnight(
            None,
            years=getattr(args, "grid_years", 2.0),
            years_1m=getattr(args, "years_1m", 0.5),
            write_reports=True,
        )
        slim = {
            k: v
            for k, v in report.items()
            if k
            not in (
                "accepted_cells",
                "okala_accepted_cells",
                "data_gaps",
            )
        }
        slim["accepted_structure_top"] = (report.get("accepted_cells") or [])[:15]
        slim["okala_accepted_top"] = (report.get("okala_accepted_cells") or [])[:10]
        print(json.dumps(slim, indent=2, default=str))
        return 0
    if cmd == "cf-india":
        from backtest_engine.cf_india_proxy import india_decision, simulate_family
        from backtest_engine.indicators import Bar

        # Synthetic bars — decision + probe shape only; full grid = cf-overnight.
        base_ts = 1704155400
        bars = [
            Bar(
                ts=base_ts + i * 60,
                open=24000 + (i % 7),
                high=24020 + (i % 7),
                low=23980 + (i % 7),
                close=24000 + ((i * 3) % 50),
                volume=1.0,
            )
            for i in range(120)
        ]
        fam = str(args.family).upper()
        cell = simulate_family(
            bars,
            family=fam,
            underlying=str(args.underlying).upper(),
            tf_min=5,
        )
        print(
            json.dumps(
                {
                    "orders": "refused",
                    "paper_only": True,
                    "NO_PROMOTE": True,
                    "note": "Sibling probe — does not rewrite okala_in_proxy; use cf-overnight for grids",
                    "openai_india_decision": india_decision(fam),
                    "cell": {k: v for k, v in cell.items() if k != "trades"},
                    "n_trades": cell.get("n"),
                },
                indent=2,
                default=str,
            )
        )
        return 0
    if cmd == "okala-signal":
        from backtest_engine.indicators import Bar
        from backtest_engine.levels import bind_option_premium_levels
        from backtest_engine.okala_in_paper import (
            PAPER_STARTER_STOP_PCT,
            PAPER_STARTER_TARGET_PCT,
            detect_okala_signal,
            okala_paper_meta,
        )

        # Synthetic bars only — prove JSON emit; no Dhan, no daemons.
        base_ts = 1704155400
        bars = [
            Bar(
                ts=base_ts + i * 60,
                open=24000 + (i % 5),
                high=24010 + (i % 5),
                low=23990 + (i % 5),
                close=24000 + (i % 5),
                volume=1.0,
            )
            for i in range(100)
        ]
        meta = {"source": "mock_dry_run", "expiry": "DRY"}
        if int(getattr(args, "strike", 0) or 0) > 0:
            meta["strike"] = int(args.strike)
        ltp = float(args.option_ltp)
        sig = detect_okala_signal(
            str(args.underlying).upper(),
            bars,
            option_ltp=ltp,
            premium_meta=meta,
            session_kind="NEWS_DAY",
            veto_reasons=["BIG_NEWS dry-run prove-not-blocked"],
        )
        premium_shape = bind_option_premium_levels(
            option_ltp=ltp,
            lean="PE",
            strike=meta.get("strike"),
            underlying_spot=float(bars[-1].close),
            target_pct=PAPER_STARTER_TARGET_PCT,
            stop_pct=PAPER_STARTER_STOP_PCT,
            expiry=meta.get("expiry"),
            premium_source="mock_dry_run",
        )
        out = {
            "orders": "refused",
            "paper_only": True,
            "research_ready_for_programming": False,
            "meta": okala_paper_meta(),
            "signal": sig,
            "premium_ticket_shape": {
                "note": "PAPER starter Entry/Stop/Target from option LTP (demo lean=PE)",
                "entry": premium_shape.get("entry"),
                "stop": premium_shape.get("stop"),
                "target": premium_shape.get("target"),
                "unit": premium_shape.get("unit"),
                "spot_underlying": premium_shape.get("underlying_spot"),
            },
            "news_day_on_purpose": True,
            "news_blocked": False,
            "note": (
                "Dry-run synthetic bars. signal=null means pattern did not form on synth "
                "(live bars needed). NEWS_DAY present on purpose — must not block when "
                "NEWS_VETO_ENABLED=false. Orders refused."
            ),
        }
        print(json.dumps(out, indent=2, default=str))
        return 0
    if cmd == "okala-in":
        # Cache-only; no Dhan client / no live fetch.
        report = run_okala_in(
            None,
            years=getattr(args, "grid_years", 2.0),
            years_1m=getattr(args, "years_1m", 0.5),
            magnet_seed=getattr(args, "magnet_seed", 20260907),
            write_reports=True,
        )
        slim = {k: v for k, v in report.items() if k != "cells"}
        print(json.dumps(slim, indent=2, default=str))
        return 0
    with DhanClient(dry_run=dry) as client:
        if cmd == "index-5m":
            report = run_default(client)
        elif cmd == "option":
            # 02 charter: 1m rollingoption resampled to spoken 2m/3m/5m. Do not default to 5.
            report = run_option_premium(client, years=args.years, interval=args.interval)
        elif cmd == "project":
            report = run_project_mixes(client, years=args.years, interval=args.interval)
        elif cmd == "scan":
            report = run_scan(client, years=args.years, interval=args.interval)
        elif cmd == "club":
            report = run_club(client, years=args.years, interval=args.interval)
        elif cmd == "honest":
            report = run_honest(client, years=args.years, interval=args.interval)
        elif cmd == "sltp":
            report = run_sltp(client, years=args.years, interval=args.interval)
        elif cmd == "cf-fabio":
            report = run_cf_fabio(client, years=args.years, interval=args.interval)
        elif cmd == "cf-marco-mayne":
            report = run_cf_marco_mayne(client, years=args.years, interval=args.interval)
        elif cmd == "cf-marci-tori":
            report = run_cf_marci_tori(client, years=args.years, interval=args.interval)
        elif cmd == "cf-tg-kane":
            report = run_cf_tg_kane(client, years=args.years, interval=args.interval)
        elif cmd == "cf-umar-forest":
            report = run_cf_umar_forest(client, years=args.years, interval=args.interval)
        elif cmd == "cf-carmine-jadecap":
            report = run_cf_carmine_jadecap(client, years=args.years, interval=args.interval)
        elif cmd == "cf-usman-brando":
            report = run_cf_usman_brando(client, years=args.years, interval=args.interval)
        elif cmd == "cf-andrea-omor":
            report = run_cf_andrea_omor(client, years=args.years, interval=args.interval)
        else:
            report = run_books(client, years=args.years, interval=args.interval)
    if cmd in (
        "option",
        "project",
        "scan",
        "club",
        "honest",
        "sltp",
        "cf-fabio",
        "cf-marco-mayne",
        "cf-marci-tori",
        "cf-tg-kane",
        "cf-umar-forest",
        "cf-carmine-jadecap",
        "cf-usman-brando",
        "cf-andrea-omor",
    ):
        slim = {k: v for k, v in report.items() if k != "books"}
        print(json.dumps(slim, indent=2, default=str))
        if cmd == "sltp":
            print(json.dumps({"books_slim": [
                {
                    "book_id": b.get("book_id"),
                    "rating": b.get("rating"),
                    "oos": b.get("oos"),
                    "all": b.get("all"),
                    "reason_breakdown": b.get("reason_breakdown"),
                }
                for b in (report.get("books") or [])
            ]}, indent=2, default=str))
    else:
        print(json.dumps(report, indent=2, default=str))
    if cmd == "index-5m":
        return 0 if all(r.get("ok") for r in report.get("books") or []) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
