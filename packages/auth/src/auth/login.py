"""Paper login: issue access+refresh from env/secretstore key. Fail closed.

Not a customer password store. Operator / 5-customer paper-portal mint only.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping

from auth.foundation import (
    PAPER_CUSTOMER_CAP,
    AuthClosed,
    TokenPair,
    issue_pair,
    issue_refresh,
    refresh_to_access,
    verify_access,
)
from auth.keys import load_totp_secret, require_jwt_secret

PAPER_CUSTOMERS_ENV = "AAD_PAPER_CUSTOMERS"


def paper_customer_allowlist(*, environ: Mapping[str, str] | None = None) -> frozenset[str]:
    env = os.environ if environ is None else environ
    raw = str(env.get(PAPER_CUSTOMERS_ENV, "") or "")
    ids = frozenset(part.strip() for part in raw.split(",") if part.strip())
    if len(ids) > PAPER_CUSTOMER_CAP:
        raise AuthClosed("paper_customer_cap")
    return ids


def login(
    *,
    role: str,
    sub: str,
    now: float | None = None,
    totp: str = "",
    secret: str | None = None,
    totp_secret: str | None = None,
    environ: Mapping[str, str] | None = None,
    store: object | None = None,
    tfa: bool | None = None,
) -> TokenPair:
    """Issue a pair. Empty signing key denies. Customer cannot take founder 2FA."""
    key = require_jwt_secret(environ=environ, store=store) if secret is None else secret
    if not key:
        raise AuthClosed("jwt_secret_missing")
    who = str(sub).strip()
    if role == "customer":
        allow = paper_customer_allowlist(environ=environ)
        if allow and who not in allow:
            raise AuthClosed("unknown_customer")
    when = time.time() if now is None else now
    seed = load_totp_secret(environ=environ) if totp_secret is None else totp_secret
    want_tfa = bool(tfa) if tfa is not None else bool(totp) and role == "founder"
    return issue_pair(
        key,
        role=role,
        sub=sub,
        now=when,
        tfa=want_tfa,
        totp_secret=seed,
        totp_code=totp,
    )


def refresh_session(
    refresh_token: str | None,
    *,
    now: float | None = None,
    secret: str | None = None,
    environ: Mapping[str, str] | None = None,
    store: object | None = None,
) -> TokenPair:
    key = require_jwt_secret(environ=environ, store=store) if secret is None else secret
    if not key:
        raise AuthClosed("jwt_secret_missing")
    when = time.time() if now is None else now
    access = refresh_to_access(refresh_token, key, when)
    decision = verify_access(access, key, when)
    if not decision.ok:
        raise AuthClosed(decision.reason or "unauthorized")
    refresh = issue_refresh(key, role=decision.role, sub=decision.sub, now=when)
    return TokenPair(
        access=access,
        refresh=refresh,
        role=decision.role,
        sub=decision.sub,
        channels=decision.channels,
    )


__all__ = [
    "PAPER_CUSTOMERS_ENV",
    "PAPER_CUSTOMER_CAP",
    "login",
    "paper_customer_allowlist",
    "refresh_session",
]
