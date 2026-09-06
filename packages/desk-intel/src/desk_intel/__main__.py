"""CLI: PRE_MARKET (morning) + POST_MARKET (nightly recon). Never prints secrets.

  python -m desk_intel morning --offline
  python -m desk_intel pre-market --offline
  python -m desk_intel nightly --offline
  python -m desk_intel post-market --offline
  python -m jobs pre-market --offline
  python -m jobs post-market --offline
  python -m desk_intel poll-chain --interval 3m --offline
  python -m desk_intel status
  python -m desk_intel audit-docs
  python -m desk_intel eod-recon --day 2026-09-06
  python -m docs_auditor
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import Optional

from dhan_client.client import DhanClient
from dhan_client.config import (
    ENV_ACCESS_TOKEN,
    ENV_CLIENT_ID,
    ENV_CLIENT_SECRET,
    ENV_REFRESH_TOKEN,
    load_settings,
)

from desk_intel.docs_audit import attach_docs_audit
from desk_intel.fusion import fuse
from desk_intel.news_ingest import ingest_news
from desk_intel.nightly import run_nightly
from desk_intel.option_chain_poller import poll_underlyings
from desk_intel.paper_signal import to_paper_desk
from desk_intel.premarket import gather_premarket
from desk_intel.schema import PollMode
from desk_intel.store import save_signals
from desk_intel.workspace import (
    load_desk_workspace,
    parse_interval_seconds,
)

log = logging.getLogger("desk_intel")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _print(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def _dry_flag(args: argparse.Namespace) -> Optional[bool]:
    if getattr(args, "live", False):
        return False
    if getattr(args, "dry_run", False):
        return True
    return None


def cmd_status(args: argparse.Namespace) -> int:
    settings = load_settings(dry_run=_dry_flag(args))
    cfg = load_desk_workspace()
    creds = settings.credentials
    _print(
        {
            "dry_run": settings.dry_run,
            "env_set": {
                ENV_CLIENT_ID: bool(creds.client_id),
                ENV_ACCESS_TOKEN: bool(creds.access_token),
                ENV_REFRESH_TOKEN: bool(creds.refresh_token),
                ENV_CLIENT_SECRET: bool(creds.client_secret),
            },
            "news_sources_enabled": [
                {"id": s.id, "url": s.url, "kind": s.kind}
                for s in cfg.news_sources
                if s.enabled
            ],
            "tape_sources": {
                "gift_nifty": [
                    {"id": s.id, "kind": s.kind, "url": s.url}
                    for s in cfg.gift_sources
                    if s.enabled
                ],
                "pre_open": [
                    {"id": s.id, "kind": s.kind, "url": s.url}
                    for s in cfg.pre_open_sources
                    if s.enabled
                ],
                "global_tape": [
                    {"id": s.id, "kind": s.kind, "url": s.url}
                    for s in cfg.global_tape_sources
                    if s.enabled
                ],
            },
            "jobs": {
                "pre_market": {
                    "enabled": cfg.jobs.pre_market.enabled,
                    "before_ist": cfg.jobs.pre_market.before_ist,
                },
                "post_market": {
                    "enabled": cfg.jobs.post_market.enabled,
                    "after_ist": cfg.jobs.post_market.after_ist,
                    "session_close_ist": cfg.jobs.post_market.session_close_ist,
                },
                "docs_auditor": {
                    "enabled": cfg.jobs.docs_auditor.enabled,
                    "cadence": cfg.jobs.docs_auditor.cadence,
                },
            },
            "poll": {
                "chain_interval": cfg.desk_intel.chain_interval,
                "strike_buildup_interval": cfg.desk_intel.strike_buildup_interval,
                "strike_buildup_enabled": cfg.desk_intel.strike_buildup_enabled,
                "remember_last_snapshot": cfg.desk_intel.remember_last_snapshot,
                "atm_wing": cfg.desk_intel.atm_wing,
                "option_chain_min_seconds": cfg.desk_intel.option_chain_min_seconds,
                "sentiment_windows": cfg.desk_intel.sentiment_windows,
            },
            "markets": [
                {
                    "id": m.id,
                    "enabled": m.enabled,
                    "dhan_underlying_scrip_set": m.dhan_underlying_scrip is not None,
                    "seg": m.dhan_underlying_seg,
                }
                for m in cfg.markets
            ],
            "compliance": "Education ≠ advice. Tokens never logged.",
            "persona": "teams/00_orchestrator/docs/PERSONA_DESK.md",
        }
    )
    return 0


def _run_cycle(
    *,
    mode: PollMode,
    offline: bool,
    dry_run: Optional[bool],
    persist: bool,
    suffix: str,
    include_premarket: bool = False,
) -> dict:
    cfg = load_desk_workspace()
    events = ingest_news(cfg, offline=offline, allow_fixtures=True)
    brief = None
    if include_premarket or mode in ("morning", "pre_market"):
        brief = gather_premarket(cfg, events, offline=offline)
    chain_mode: PollMode = "morning" if mode == "pre_market" else mode
    with DhanClient(dry_run=dry_run) as client:
        pairs = poll_underlyings(cfg, client, mode=chain_mode, persist=persist)
    biases = [b for _, b in pairs]
    signals = fuse(biases, events, cfg.desk_intel)
    paper = to_paper_desk(signals)
    written = None
    if persist:
        written = str(save_signals(cfg.repo_root, cfg.desk_intel.signals_dir, signals, suffix=suffix))
    payload = {
        "job": "PRE_MARKET" if mode in ("morning", "pre_market") else mode,
        "mode": mode,
        "dhan_dry_run": pairs[0][0].dry_run if pairs else True,
        "news_count": len(events),
        "news_offline": offline,
        "signal_path": written,
        "paper_desk": paper,
        "compliance": signals[0].compliance if signals else "",
        "execution": "refused",
    }
    if brief is not None:
        payload["premarket"] = brief.to_dict()
        payload["regime_note"] = brief.regime_note
        payload["tape_missing"] = brief.missing
    return payload


def cmd_morning(args: argparse.Namespace) -> int:
    payload = _run_cycle(
        mode="morning",
        offline=args.offline,
        dry_run=_dry_flag(args),
        persist=not args.no_save,
        suffix="morning",
        include_premarket=True,
    )
    _print(payload)
    return 0


def cmd_pre_market(args: argparse.Namespace) -> int:
    payload = _run_cycle(
        mode="pre_market",
        offline=args.offline,
        dry_run=_dry_flag(args),
        persist=not args.no_save,
        suffix="pre_market",
        include_premarket=True,
    )
    _print(payload)
    return 0


def cmd_eod_recon(args: argparse.Namespace) -> int:
    """Thin alias → agent_rag eod-recon. No production param writes."""
    try:
        from agent_rag.eod_recon import run_eod_recon
    except ImportError:
        print(
            json.dumps(
                {
                    "error": "agent_rag not installed — pip install -e packages/agent_rag",
                    "retune_proposal": {"status": "BACKTEST_REQUIRED"},
                    "promote": False,
                }
            )
        )
        return 1
    out = run_eod_recon(
        day=(getattr(args, "day", None) or None) or None,
        offline=True,
        update_continue=not bool(getattr(args, "no_continue", False)),
    )
    print(json.dumps(out, indent=2, default=str))
    return 0


def cmd_nightly(args: argparse.Namespace) -> int:
    cfg = load_desk_workspace()
    fixture_signals = None
    events = None
    if args.offline:
        # Ensure a paper trail when no live tokens / empty signal dir.
        cycle = _run_cycle(
            mode="morning",
            offline=True,
            dry_run=True,
            persist=not args.no_save,
            suffix="nightly_seed",
            include_premarket=True,
        )
        from desk_intel.store import market_signal_from_dict

        fixture_signals = [
            market_signal_from_dict(row)
            for row in (cycle.get("paper_desk") or {}).get("market_signals") or []
        ]
        events = ingest_news(cfg, offline=True, allow_fixtures=True)
    payload = run_nightly(
        cfg,
        persist=not args.no_save,
        fixture_signals=fixture_signals,
        session_expired=True,
        events=events,
    )
    # Standing Docs Auditor — every nightly / post-market (cadence: daily).
    audit = attach_docs_audit(cfg.repo_root, write=True)
    payload["docs_audit"] = {
        "ok": audit.get("ok"),
        "finding_count": audit.get("finding_count"),
        "report_path": audit.get("report_path"),
        "checks_run": audit.get("checks_run"),
        "findings": audit.get("findings"),
        "compliance": audit.get("compliance"),
    }
    _print(payload)
    return 0 if audit.get("ok") else 1


def cmd_audit_docs(args: argparse.Namespace) -> int:
    cfg = load_desk_workspace()
    audit = attach_docs_audit(cfg.repo_root, write=True)
    _print(audit)
    return 0 if audit.get("ok") else 1


def cmd_ingest_news(args: argparse.Namespace) -> int:
    cfg = load_desk_workspace()
    events = ingest_news(cfg, offline=args.offline, allow_fixtures=True)
    _print([e.to_dict() for e in events])
    return 0


def cmd_poll_chain(args: argparse.Namespace) -> int:
    cfg = load_desk_workspace()
    interval_raw = args.interval or cfg.desk_intel.chain_interval
    seconds = parse_interval_seconds(interval_raw, 180)
    full_chain = bool(args.full_chain)
    if seconds <= 90 and not full_chain:
        mode: PollMode = "strike_buildup_1m"
        log.info(
            "interval=%ss → 1m strike-buildup (ATM±%s via quote / cached delta). "
            "Not a full option-chain poll. Pass --full-chain to override (rate-limited 1/3s, not recommended).",
            seconds,
            cfg.desk_intel.atm_wing,
        )
    else:
        mode = "full_chain_3m"
        if seconds <= 90 and full_chain:
            log.warning(
                "Full POST /optionchain every %ss burns the 1 unique-request / 3s budget. "
                "Default remains 3m. OI updates slowly (Dhan docs).",
                seconds,
            )

    def once() -> dict:
        return _run_cycle(
            mode=mode,
            offline=args.offline,
            dry_run=_dry_flag(args),
            persist=not args.no_save,
            suffix=mode,
        )

    payload = once()
    _print(payload)
    if not args.loop:
        return 0
    log.info("loop every %ss Ctrl-C to stop (no orders)", seconds)
    try:
        while True:
            time.sleep(seconds)
            payload = once()
            _print(payload)
    except KeyboardInterrupt:
        log.info("stopped")
        return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Force no Dhan HTTP (fixtures for chain).",
    )
    common.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Require DHAN_CLIENT_ID + DHAN_ACCESS_TOKEN and call Dhan.",
    )
    common.add_argument(
        "--offline",
        action="store_true",
        default=False,
        help="Skip RSS; use packaged news fixtures.",
    )
    common.add_argument(
        "--no-save",
        action="store_true",
        default=False,
        help="Do not write data/desk_intel snapshots/signals.",
    )
    parser = argparse.ArgumentParser(
        prog="desk_intel",
        description=(
            "PRE_MARKET news+tape+chain → MARKET_SIGNAL; POST_MARKET nightly recon. "
            "Education ≠ advice. No orders. Shadow paper only."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "status",
        parents=[common],
        help="Env name flags + yaml poll/news/jobs (no secret values).",
    )
    sub.add_parser(
        "morning",
        parents=[common],
        help="PRE_MARKET: news + GIFT/SGX/global/pre-open (VERIFY) + chain + fuse.",
    )
    sub.add_parser(
        "pre-market",
        parents=[common],
        help="Alias of morning (jobs.pre_market).",
    )
    sub.add_parser(
        "nightly",
        parents=[common],
        help="POST_MARKET recon + PhD handoff, then Docs Auditor. No orders.",
    )
    sub.add_parser(
        "post-market",
        parents=[common],
        help="Alias of nightly (jobs.post_market). Ends with Docs Auditor.",
    )
    sub.add_parser(
        "audit-docs",
        help="Standing Docs Auditor (09). Exit 1 if STALE/MISSING/CONTRADICTS.",
    )
    eod = sub.add_parser(
        "eod-recon",
        parents=[common],
        help=(
            "EOD stub: paper ledger → session tag → RETUNE_PROPOSAL "
            "BACKTEST_REQUIRED (agent_rag). No auto-retune."
        ),
    )
    eod.add_argument(
        "--day",
        default="",
        help="YYYY-MM-DD (default IST today). Alias of python -m agent_rag eod-recon.",
    )
    eod.add_argument(
        "--no-continue",
        action="store_true",
        help="Do not patch CONTINUE_NEXT_CHAT.md",
    )
    sub.add_parser(
        "ingest-news",
        parents=[common],
        help="RSS/official feeds only (or --offline fixtures).",
    )
    poll = sub.add_parser(
        "poll-chain",
        parents=[common],
        help="3m full chain (default) or 1m ATM±N buildup.",
    )
    poll.add_argument(
        "--interval",
        default=None,
        help="3m (full chain, default) or 1m (strike-buildup ATM±N). Default from workspace.yaml.",
    )
    poll.add_argument(
        "--loop",
        action="store_true",
        help="Repeat until Ctrl-C. Sleeps the real interval.",
    )
    poll.add_argument(
        "--full-chain",
        action="store_true",
        help="On 1m interval, still call POST /optionchain (rate-limited; not default).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    _configure_logging()
    args = build_parser().parse_args(argv)
    commands = {
        "status": cmd_status,
        "morning": cmd_morning,
        "pre-market": cmd_pre_market,
        "nightly": cmd_nightly,
        "post-market": cmd_nightly,
        "eod-recon": cmd_eod_recon,
        "audit-docs": cmd_audit_docs,
        "ingest-news": cmd_ingest_news,
        "poll-chain": cmd_poll_chain,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
