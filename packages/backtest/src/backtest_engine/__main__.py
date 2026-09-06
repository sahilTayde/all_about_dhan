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
from backtest_engine.run_cf_fabio import run_cf_fabio
from backtest_engine.run_cf_marco_mayne import run_cf_marco_mayne
from backtest_engine.run_cf_marci_tori import run_cf_marci_tori
from backtest_engine.run_cf_tg_kane import run_cf_tg_kane
from backtest_engine.run_cf_umar_forest import run_cf_umar_forest
from backtest_engine.run_cf_carmine_jadecap import run_cf_carmine_jadecap
from backtest_engine.run_cf_usman_brando import run_cf_usman_brando
from backtest_engine.run_cf_andrea_omor import run_cf_andrea_omor


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
    args = parser.parse_args(argv)
    dry: bool | None
    if args.live:
        dry = False
    elif args.dry_run:
        dry = True
    else:
        dry = None
    cmd = args.cmd or "books"
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
