"""CLI: python -m agent_rag …"""

from __future__ import annotations

import argparse
import json
import sys


def cmd_rebuild(_args: argparse.Namespace) -> int:
    from agent_rag.ingest import rebuild

    report = rebuild()
    print(json.dumps(report, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    from agent_rag.query import hits_as_dicts, query

    try:
        hits = query(args.text, limit=args.limit, kind=args.kind or None)
    except FileNotFoundError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"q": args.text, "n": len(hits), "hits": hits_as_dicts(hits)},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_paper_backtest(args: argparse.Namespace) -> int:
    from agent_rag.paper_backtest import run_paper_backtest

    out = run_paper_backtest(
        day=args.day,
        with_openai=not args.no_openai,
    )
    print(json.dumps(out, indent=2))
    return 0


def cmd_eod_recon(args: argparse.Namespace) -> int:
    from agent_rag.eod_recon import run_eod_recon

    out = run_eod_recon(
        day=args.day or None,
        offline=bool(args.offline),
        update_continue=not bool(args.no_continue),
    )
    print(json.dumps(out, indent=2))
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    from agent_rag.paths import agent_rag_db, repo_root, transcripts_db

    root = repo_root()
    rag = agent_rag_db(root)
    tdb = transcripts_db(root)
    print(
        json.dumps(
            {
                "agent_rag": str(rag.relative_to(root)),
                "agent_rag_exists": rag.is_file(),
                "transcripts_sqlite": str(tdb.relative_to(root)),
                "transcripts_exists": tdb.is_file(),
                "note": "agent_rag never writes transcripts.sqlite",
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-rag",
        description=(
            "Agent speed KB (FTS5) + paper backtest rollup + EOD recon stub. "
            "Does not touch transcripts.sqlite. No live orders."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("rebuild", help="Rebuild data/knowledge/agent_rag.sqlite")
    sub.add_parser("status", help="Show KB paths (no secrets)")

    pq = sub.add_parser("query", help='FTS5 search, e.g. query "fake breakout"')
    pq.add_argument("text", help="Search text")
    pq.add_argument("--limit", type=int, default=8)
    pq.add_argument("--kind", default="", help="Optional kind filter")

    pb = sub.add_parser(
        "paper-backtest",
        help="Roll up CF/club/sltp/honest + agents dry → recon + OpenAI notes",
    )
    pb.add_argument("--day", default="2026-09-06")
    pb.add_argument(
        "--no-openai",
        action="store_true",
        help="Skip OpenAI review (still writes rollup JSON/MD)",
    )

    pe = sub.add_parser(
        "eod-recon",
        help="Paper ledger → session tag → RETUNE_PROPOSAL BACKTEST_REQUIRED",
    )
    pe.add_argument("--day", default="", help="YYYY-MM-DD (default IST today)")
    pe.add_argument(
        "--offline",
        action="store_true",
        default=True,
        help="Do not invent live news (default)",
    )
    pe.add_argument(
        "--no-continue",
        action="store_true",
        help="Do not patch CONTINUE_NEXT_CHAT.md",
    )

    args = parser.parse_args(argv)
    commands = {
        "rebuild": cmd_rebuild,
        "status": cmd_status,
        "query": cmd_query,
        "paper-backtest": cmd_paper_backtest,
        "eod-recon": cmd_eod_recon,
    }
    return commands[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
