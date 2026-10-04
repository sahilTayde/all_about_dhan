"""python -m accounts — list / show / enable / disable paper accounts. No live broker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from accounts.errors import AccountClosed, AccountSafetyError
from accounts.model import Account
from accounts.registry import MAX_CUSTOMER_ACCOUNTS, AccountRegistry, default_config_path, set_account_status
from accounts.safety import assert_paper_only
from accounts.split import run_role_once


def _account_payload(acc: Account) -> dict[str, object]:
    return {
        "account_id": acc.account_id,
        "kind": acc.kind,
        "broker": acc.broker,
        "status": acc.status,
        "risk_budget_inr": acc.risk_budget_inr,
    }


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] not in {"-h", "--help"}:
        head = raw[0].replace("_", "-")
        if head.startswith("c5"):
            from accounts.c5 import cli

            return cli(raw)
    p = argparse.ArgumentParser(description="C5-01/C5-04 accounts (paper/shadow only; no live broker)")
    p.add_argument("command", choices=("list", "show", "enable", "disable", "signal", "exec"))
    p.add_argument("--account", default=None)
    p.add_argument("--config", default=None)
    p.add_argument("--state-dir", default=None)
    p.add_argument("--mode", default="paper")
    args = p.parse_args(raw)
    cfg = Path(args.config) if args.config else default_config_path()
    try:
        assert_paper_only(args.mode)
        if args.command == "list":
            registry = AccountRegistry.load(cfg)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "default_account": registry.default_account,
                        "accounts": [_account_payload(acc) for acc in registry.all()],
                        "customer_ids": list(registry.customer_ids()),
                        "customer_cap": MAX_CUSTOMER_ACCOUNTS,
                        "live_broker": False,
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "show":
            registry = AccountRegistry.load(cfg)
            acc = registry.get(args.account or registry.default_account)
            print(
                json.dumps(
                    {
                        "ok": True,
                        **_account_payload(acc),
                        "live_broker": False,
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.command in {"enable", "disable"}:
            if not args.account:
                raise AccountClosed("ACCOUNT_ID_REQUIRED")
            acc = set_account_status(
                args.account,
                "active" if args.command == "enable" else "disabled",
                path=cfg,
                mode=args.mode,
            )
            print(
                json.dumps(
                    {
                        "ok": True,
                        **_account_payload(acc),
                        "live_broker": False,
                    },
                    sort_keys=True,
                )
            )
            return 0
        body = run_role_once(
            role=args.command,
            account_id=args.account,
            state_dir=Path(args.state_dir) if args.state_dir else None,
            config_path=cfg,
            mode=args.mode,
        )
        print(json.dumps(body, sort_keys=True))
        return 0 if body.get("ok") else 1
    except (AccountSafetyError, AccountClosed) as exc:
        print(json.dumps({"ok": False, "reason": str(exc), "orders": "REFUSED"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
