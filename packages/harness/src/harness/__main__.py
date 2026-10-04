"""python -m harness — off-market LIMIT submit+cancel. Default OFF. Never prints secrets."""

from __future__ import annotations

import argparse
import json
import os
import sys

from harness.gates import EXIT_OK, EXIT_ORDER_PATH, EXIT_REFUSED, HarnessRefused, require_transport
from harness.order import (
    DEFAULT_OFF_MARKET_LIMIT,
    MAX_OFF_MARKET_LIMIT,
    HarnessOrderError,
    OffMarketIntent,
)
from harness.run import run_shadow_test


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "V2-25 Dhan off-market shadow order harness. Default OFF. "
            "CI must use --transport mock. Live Dhan requires founder approval + credentials."
        )
    )
    p.add_argument("--mode", default="", help="shadow or harness (live/limited_live refused)")
    p.add_argument(
        "--transport",
        default="none",
        help="none (default, refuse) | mock | recorded | dhan",
    )
    p.add_argument(
        "--security-id",
        default="",
        help="Dhan securityId; required for --transport dhan",
    )
    p.add_argument("--symbol", default="NIFTY CE")
    p.add_argument("--limit-price", type=float, default=DEFAULT_OFF_MARKET_LIMIT)
    p.add_argument("--lots", type=int, default=1)
    p.add_argument("--lot-size", type=int, default=1)
    p.add_argument("--count", type=int, default=1, help="1..5 submit+cancel cycles")
    return p


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parser().parse_args(raw)
        transport = require_transport(args.transport)
        security_id = (args.security_id or "").strip()
        if transport == "dhan" and not security_id:
            raise HarnessRefused(
                "SECURITY_ID_MISSING",
                "live transport needs --security-id from the founder",
            )
        if not security_id:
            security_id = "TEST"
        if args.limit_price > MAX_OFF_MARKET_LIMIT:
            raise HarnessOrderError(
                f"limit_price {args.limit_price} exceeds off-market cap {MAX_OFF_MARKET_LIMIT}"
            )
        intent = OffMarketIntent(
            symbol=args.symbol,
            security_id=security_id,
            limit_price=float(args.limit_price),
            lots=int(args.lots),
            lot_size=int(args.lot_size),
        )
        result = run_shadow_test(
            mode=args.mode,
            env=os.environ,
            transport=transport,
            intent=intent,
            count=int(args.count),
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "submitted": result.submitted,
                    "cancelled": result.cancelled,
                    "fills": result.fills,
                    "transport": result.transport,
                    "states": list(result.states),
                },
                sort_keys=True,
            )
        )
        return EXIT_OK if result.ok and result.fills == 0 else EXIT_ORDER_PATH
    except HarnessRefused as exc:
        print(f"harness refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except HarnessOrderError as exc:
        print(f"harness order-path failed: {exc}", file=sys.stderr)
        return EXIT_ORDER_PATH
    except Exception:
        print("harness failed: unexpected error (secrets not printed)", file=sys.stderr)
        return EXIT_ORDER_PATH


if __name__ == "__main__":
    raise SystemExit(main())
