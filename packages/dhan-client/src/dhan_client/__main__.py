"""CLI: inspect dry-run wiring without a live token.

Never prints secret values.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Optional

from dhan_client.client import DhanClient
from dhan_client.config import (
    ENV_ACCESS_TOKEN,
    ENV_CLIENT_ID,
    ENV_CLIENT_SECRET,
    ENV_REFRESH_TOKEN,
    load_settings,
)
from dhan_client.errors import SafeModeError
from dhan_client.paper_probe import run_paper_probe
from dhan_client.futidx import contracts_as_dicts, parse_futidx_csv
from dhan_client.types import FeedInstrument, FeedMode

# Official live-market-feed example instrument (not an index-options strategy).
_DOCS_SAMPLE = FeedInstrument(exchange_segment="NSE_EQ", security_id="1333")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _print(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_status(dry_run: Optional[bool]) -> int:
    settings = load_settings(dry_run=dry_run)
    creds = settings.credentials
    _print(
        {
            "dry_run": settings.dry_run,
            "api_base": settings.api_base,
            "feed_ws_base": settings.feed_ws_base,
            "env_set": {
                ENV_CLIENT_ID: bool(creds.client_id),
                ENV_ACCESS_TOKEN: bool(creds.access_token),
                ENV_REFRESH_TOKEN: bool(creds.refresh_token),
                ENV_CLIENT_SECRET: bool(creds.client_secret),
            },
            "refresh": (
                "VERIFY FROM DOCS — dhan_client.refresh; "
                "https://dhanhq.co/docs/v2/authentication/"
            ),
        }
    )
    return 0


def cmd_quote(dry_run: Optional[bool]) -> int:
    with DhanClient(dry_run=dry_run) as client:
        body = {"NSE_EQ": [1333]}
        _print(
            {
                "ltp": client.quote.ltp(body),
                "ohlc": client.quote.ohlc(body),
                "quote": client.quote.quote(body),
            }
        )
    return 0


def cmd_historical(dry_run: Optional[bool]) -> int:
    with DhanClient(dry_run=dry_run) as client:
        _print(
            client.historical.daily(
                {
                    "securityId": "1333",
                    "exchangeSegment": "NSE_EQ",
                    "instrument": "EQUITY",
                    "fromDate": "2022-01-08",
                    "toDate": "2022-02-08",
                }
            )
        )
    return 0


def cmd_option_chain(dry_run: Optional[bool]) -> int:
    with DhanClient(dry_run=dry_run) as client:
        _print(
            {
                "expiry_list": client.option_chain.expiry_list(
                    {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"}
                ),
                "chain": client.option_chain.chain(
                    {
                        "UnderlyingScrip": 13,
                        "UnderlyingSeg": "IDX_I",
                        "Expiry": "2024-10-31",
                    }
                ),
            }
        )
    return 0


def cmd_feed(dry_run: Optional[bool]) -> int:
    async def _run() -> None:
        client = DhanClient(dry_run=dry_run)
        feed = client.feed_collector(
            [_DOCS_SAMPLE], mode=FeedMode.TICKER, reconnect=False
        )

        def on_packet(pkt: object) -> None:
            _print(pkt)

        await feed.run(on_packet)

    asyncio.run(_run())
    return 0


def cmd_profile(dry_run: Optional[bool]) -> int:
    with DhanClient(dry_run=dry_run) as client:
        raw = client.profile.get()
        _print({"ok": True, "keys": sorted(raw.keys()) if isinstance(raw, dict) else type(raw).__name__})
    return 0


def cmd_paper_probe(dry_run: Optional[bool]) -> int:
    from dhan_client.config import repo_root

    with DhanClient(dry_run=dry_run) as client:
        report = run_paper_probe(client)
    _print(report)
    root = repo_root()
    out_dir = root / "data" / "recon"
    out_dir.mkdir(parents=True, exist_ok=True)
    day = report.get("as_of_ist", "")[:10] or "unknown"
    path = out_dir / f"PAPER_PROBE_{day}.json"
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return 0 if report.get("orders", {}).get("place_order_refused") else 1


def cmd_futidx(dry_run: Optional[bool]) -> int:
    with DhanClient(dry_run=dry_run) as client:
        if client.dry_run:
            _print({"ok": False, "dry_run": True, "note": "CSV download skipped."})
            return 0
        text = client.instruments.fetch_scrip_master_text(detailed=True)
        contracts = parse_futidx_csv(text)
        if len(contracts) < 3:
            compact = client.instruments.fetch_scrip_master_text(detailed=False)
            contracts = {**parse_futidx_csv(compact), **contracts}
        _print(
            {
                "ok": len(contracts) == 3,
                "contracts": contracts_as_dicts(contracts),
                "note": "Nearest unexpired FUTIDX from public scrip-master. Not hardcoded.",
            }
        )
        return 0 if contracts else 1


def cmd_execution(dry_run: Optional[bool]) -> int:
    with DhanClient(dry_run=dry_run) as client:
        try:
            client.execution.place_order()
        except SafeModeError as exc:
            _print({"refused": True, "error": str(exc)})
            return 0
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dhan-client",
        description="DhanHQ v2 skeleton. Default is dry-run when tokens are empty.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Force dry-run (no HTTP / no WebSocket).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Require DHAN_CLIENT_ID + DHAN_ACCESS_TOKEN and call Dhan.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show dry-run flag and which env names are set.")
    sub.add_parser("quote", help="POST /marketfeed/{ltp,ohlc,quote} (or dry-run envelope).")
    sub.add_parser("historical", help="POST /charts/historical sample body.")
    sub.add_parser("option-chain", help="POST /optionchain and /optionchain/expirylist.")
    sub.add_parser("feed", help="WebSocket collector dry-run (docs sample NSE_EQ/1333).")
    sub.add_parser("execution", help="Confirm SafeMode refuses place_order.")
    sub.add_parser("profile", help="GET /profile — prints keys only, never token values.")
    sub.add_parser("paper-probe", help="Live Data API paper probe (NIFTY/BN/SENSEX yaml scrips). No orders. Writes data/recon/PAPER_PROBE_*.json")
    sub.add_parser("futidx", help="Resolve nearest NIFTY/BANKNIFTY/SENSEX FUTIDX IDs from public CSV.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    _configure_logging()
    args = build_parser().parse_args(argv)
    if args.live:
        dry_run: Optional[bool] = False
    elif args.dry_run:
        dry_run = True
    else:
        dry_run = None

    commands = {
        "status": cmd_status,
        "quote": cmd_quote,
        "historical": cmd_historical,
        "option-chain": cmd_option_chain,
        "feed": cmd_feed,
        "execution": cmd_execution,
        "profile": cmd_profile,
        "paper-probe": cmd_paper_probe,
        "futidx": cmd_futidx,
    }
    return commands[args.command](dry_run)


if __name__ == "__main__":
    sys.exit(main())
