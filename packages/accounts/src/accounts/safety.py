"""Paper/shadow only. Never construct a live Dhan broker."""

from __future__ import annotations

import sys

from accounts.errors import AccountClosed, AccountSafetyError
from accounts.model import BROKERS, LIVE_BROKERS, Account

ALLOWED_MODES = frozenset({"paper", "shadow", "replay"})
LIVE_MODES = frozenset({"live", "limited_live", "dhan"})
_FORBIDDEN_IMPORT_PREFIXES = ("brokers.dhan",)


def assert_paper_only(mode: str) -> str:
    cleaned = (mode or "").strip().lower()
    if cleaned in LIVE_MODES or cleaned in LIVE_BROKERS:
        raise AccountSafetyError(f"V2 accounts fail-closed: mode {mode!r} is live and cannot start")
    if cleaned not in ALLOWED_MODES:
        raise AccountSafetyError(f"V2 accounts fail-closed: mode {mode!r} is not paper/shadow/replay")
    return cleaned


def refuse_broker_name(name: str) -> str:
    cleaned = (name or "").strip().lower()
    if cleaned in LIVE_BROKERS or cleaned in LIVE_MODES:
        raise AccountSafetyError(f"V2 accounts fail-closed: broker {name!r} is not paper")
    if cleaned not in BROKERS:
        raise AccountSafetyError(f"V2 accounts fail-closed: broker {name!r} is not paper|shadow")
    return cleaned


def assert_no_live_modules() -> None:
    loaded = set(sys.modules)
    for name in _FORBIDDEN_IMPORT_PREFIXES:
        if name in loaded or any(mod == name or mod.startswith(name + ".") for mod in loaded):
            raise AccountSafetyError(f"V2 accounts fail-closed: {name} is loaded; no live broker path")


def assert_active(account: Account) -> Account:
    refuse_broker_name(account.broker)
    if account.status != "active":
        raise AccountClosed(f"ACCOUNT_{account.status.upper()}")
    return account
