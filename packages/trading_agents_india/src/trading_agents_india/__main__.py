"""CLI: python -m trading_agents_india …"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_session(args: argparse.Namespace) -> int:
    from trading_agents_india.pipeline import run_session

    underlyings = None
    if args.underlying:
        underlyings = [u.strip().upper() for u in args.underlying.split(",") if u.strip()]
    mode = getattr(args, "mode", None) or ("PAPER" if args.dry_run or args.paper else "PAPER")
    if getattr(args, "live", False):
        mode = "LIVE"
    result = run_session(
        underlyings=underlyings,
        dry_run=bool(args.dry_run) and mode != "LIVE",
        use_llm=bool(args.use_llm),
        prefer_desk=bool(args.prefer_desk),
        gather_india_news=bool(args.gather_news),
        prefer_live_chain=bool(getattr(args, "live_chain", False)),
        persist=not bool(args.no_persist),
        mode=mode,
    )
    payload = result.to_dict()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_market_hours(args: argparse.Namespace) -> int:
    """IST poll loop (or dry simulation). Appends paper_watch + sqlite."""
    from trading_agents_india.session_clock import DEFAULT_TICK_SECONDS
    from trading_agents_india.session_runner import run_market_hours_loop

    underlyings = None
    if args.underlying:
        underlyings = [u.strip().upper() for u in args.underlying.split(",") if u.strip()]
    mode = (args.mode or "PAPER").strip().upper()
    if getattr(args, "live", False):
        mode = "LIVE"
    tick = int(args.tick_seconds) if args.tick_seconds else DEFAULT_TICK_SECONDS
    result = run_market_hours_loop(
        underlyings=underlyings,
        mode=mode,
        tick_seconds=tick,
        max_ticks=int(args.max_ticks),
        simulate=bool(args.simulate),
        use_llm=bool(args.use_llm),
        prefer_desk=bool(args.prefer_desk),
        gather_india_news=bool(args.gather_news),
        prefer_live_chain=bool(args.live_chain),
        persist=not bool(args.no_persist),
        write_paper_watch=not bool(args.no_paper_watch),
        stop_outside_shell=bool(args.stop_outside_shell),
    )
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


def cmd_review_plan(args: argparse.Namespace) -> int:
    """Ask OpenAI to review the adoption design; write notes under teams/09_review/docs/."""
    from trading_agents_india.config import load_settings
    from trading_agents_india.llm import LlmClient
    from trading_agents_india.review import build_review_markdown, run_frontier_review

    settings = load_settings()
    adopt_path = settings.repo_root / "teams/00_orchestrator/docs/ADOPT_TRADINGAGENTS.md"
    out_path = (
        Path(args.out)
        if args.out
        else settings.repo_root
        / "teams/09_review/docs/TRADINGAGENTS_ADOPTION_REVIEW_2026-09-06.md"
    )
    adopt_text = adopt_path.read_text(encoding="utf-8") if adopt_path.is_file() else ""
    llm = LlmClient(settings.openai_model, enabled=True)
    review = run_frontier_review(adopt_text=adopt_text, llm=llm)
    md = build_review_markdown(review, openai_key_present=settings.openai_key_present)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(json.dumps({"wrote": str(out_path), "openai_used": review.get("openai_used")}, indent=2))
    return 0


def cmd_personas(_args: argparse.Namespace) -> int:
    from trading_agents_india.personas import registry_payload

    print(json.dumps({"personas": registry_payload(), "external": "TradingAgents Apache-2.0"}, indent=2))
    return 0


def cmd_clock(_args: argparse.Namespace) -> int:
    from trading_agents_india.session_clock import snapshot

    print(json.dumps(snapshot().to_dict(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="trading-agents-india",
        description=(
            "India index-options multi-agent paper signals "
            "(TradingAgents-inspired; no live orders)."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _add_common_session_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--use-llm", action="store_true", help="Call OpenAI when key present")
        p.add_argument(
            "--prefer-desk",
            action="store_true",
            help="Try desk_intel news fixtures before pure local fixtures",
        )
        p.add_argument(
            "--gather-news",
            action="store_true",
            help="Probe Dhan news API (DI if absent) + Moneycontrol via desk_intel RSS",
        )
        p.add_argument(
            "--live-chain",
            action="store_true",
            help="Try Dhan optionchain + OPTIDX premium; else fixtures / INDEX proxy",
        )
        p.add_argument("--underlying", default="", help="Comma list: NIFTY,BANKNIFTY,SENSEX")
        p.add_argument("--no-persist", action="store_true")

    p_sess = sub.add_parser("session", help="Run one paper/dry agent session loop")
    p_sess.add_argument("--dry-run", action="store_true", default=True)
    p_sess.add_argument("--paper", action="store_true", help="Mark mode=PAPER (still no orders)")
    p_sess.add_argument(
        "--live",
        action="store_true",
        help="Request mode=LIVE (always refuses orders; documents DhanHQ-only stub)",
    )
    p_sess.add_argument(
        "--mode",
        default="",
        help="PAPER|LIVE (default PAPER). LIVE always refuses orders.",
    )
    _add_common_session_flags(p_sess)
    p_sess.set_defaults(func=cmd_session)

    p_mh = sub.add_parser(
        "market-hours",
        help="IST market-hours poll loop (paper ledger); use --simulate for dry ticks",
    )
    p_mh.add_argument("--mode", default="PAPER", help="PAPER|LIVE (LIVE refuses)")
    p_mh.add_argument("--live", action="store_true", help="Force mode=LIVE (refuses)")
    p_mh.add_argument(
        "--tick-seconds",
        type=int,
        default=0,
        help="Poll interval (default 45; clamp 30–300). Path to 15s documented, not default.",
    )
    p_mh.add_argument("--max-ticks", type=int, default=1, help="Number of graph re-runs")
    p_mh.add_argument(
        "--simulate",
        action="store_true",
        help="Dry session simulation: no sleep; mid-window clock; still writes ledger unless --no-*",
    )
    p_mh.add_argument(
        "--stop-outside-shell",
        action="store_true",
        help="Exit loop when outside 09:00–15:30 IST (ignored with --simulate)",
    )
    p_mh.add_argument("--no-paper-watch", action="store_true")
    _add_common_session_flags(p_mh)
    p_mh.set_defaults(func=cmd_market_hours)

    p_rev = sub.add_parser("review-plan", help="Frontier review of adoption plan → 09 docs")
    p_rev.add_argument("--out", default="")
    p_rev.set_defaults(func=cmd_review_plan)

    p_per = sub.add_parser("personas", help="Print TradingAgents→India persona registry")
    p_per.set_defaults(func=cmd_personas)

    p_clk = sub.add_parser("clock", help="Print IST session / dead-band snapshot")
    p_clk.set_defaults(func=cmd_clock)

    args = parser.parse_args(argv)
    if getattr(args, "paper", False) and not getattr(args, "live", False):
        args.dry_run = False
        if not getattr(args, "mode", None):
            args.mode = "PAPER"
    if hasattr(args, "mode"):
        mode_val = str(args.mode or "").strip().upper()
        args.mode = mode_val or None
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
