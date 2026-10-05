"""python -m auth — paper login / refresh. Never prints the signing key."""

from __future__ import annotations

import argparse
import json
import sys
import time

from auth.foundation import AuthClosed
from auth.login import login, refresh_session


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "C5-02 paper auth (5 customers + founder). Issue access+refresh JWTs. "
            "Reads AAD_JWT_SECRET / AAD_JWT_SECRET_FILE or secretstore. "
            "Empty key denies. No live orders."
        )
    )
    sub = p.add_subparsers(dest="command", required=True)
    login_p = sub.add_parser("login", help="issue access+refresh for founder|customer")
    login_p.add_argument("--role", required=True, choices=("founder", "customer"))
    login_p.add_argument("--sub", required=True, help="subject / paper customer id")
    login_p.add_argument("--totp", default="", help="founder TOTP (required for tfa access)")
    login_p.add_argument("--now", type=float, default=None, help="unix ts (tests)")
    ref = sub.add_parser("refresh", help="rotate access from a refresh JWT")
    ref.add_argument("--token", required=True, help="refresh JWT")
    ref.add_argument("--now", type=float, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    now = args.now if args.now is not None else time.time()
    try:
        if args.command == "login":
            pair = login(role=args.role, sub=args.sub, now=now, totp=args.totp)
        else:
            pair = refresh_session(args.token, now=now)
    except AuthClosed as exc:
        print(json.dumps({"ok": False, "reason": str(exc), "orders": "REFUSED"}), file=sys.stderr)
        return 2
    print(json.dumps(pair.as_public_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
