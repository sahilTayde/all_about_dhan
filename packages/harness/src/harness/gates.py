"""Fail-closed gates. Missing flag, credentials, or mode refuses. Never logs secrets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

APPROVAL_ENV = "ALL_ABOUT_DHAN_SHADOW_HARNESS"
APPROVAL_VALUE = "I_APPROVE_OFF_MARKET_SHADOW_TEST"
CLIENT_ID_ENV = "DHAN_CLIENT_ID"
ACCESS_TOKEN_ENV = "DHAN_ACCESS_TOKEN"

ALLOWED_MODES = frozenset({"shadow", "harness"})
REFUSED_MODES = frozenset({"live", "limited_live", "dhan", "paper", "replay", ""})
ALLOWED_TRANSPORTS = frozenset({"mock", "recorded", "dhan"})

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_ORDER_PATH = 3


class HarnessRefused(Exception):
    """Fail closed. ``exit_code`` is 2. Message never includes credential values."""

    exit_code = EXIT_REFUSED

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code
        self.message = message


@dataclass(frozen=True)
class GateDecision:
    ok: bool
    reason_code: str
    message: str
    mode: str
    client_id_set: bool
    access_token_set: bool


def _clean(value: str | None) -> str:
    return (value or "").strip()


def approval_granted(env: Mapping[str, str]) -> bool:
    return _clean(env.get(APPROVAL_ENV)) == APPROVAL_VALUE


def credentials_present(env: Mapping[str, str]) -> tuple[bool, bool]:
    return bool(_clean(env.get(CLIENT_ID_ENV))), bool(_clean(env.get(ACCESS_TOKEN_ENV)))


def evaluate_gates(*, mode: str, env: Mapping[str, str]) -> GateDecision:
    """Return a decision. Never copies token values onto the result."""
    cleaned = _clean(mode).lower()
    client_set, token_set = credentials_present(env)
    if not approval_granted(env):
        return GateDecision(
            False,
            "APPROVAL_MISSING",
            f"{APPROVAL_ENV} is not set to the founder approval phrase; harness is OFF",
            cleaned,
            client_set,
            token_set,
        )
    if cleaned in REFUSED_MODES or cleaned not in ALLOWED_MODES:
        return GateDecision(
            False,
            "MODE_REFUSED",
            f"mode {cleaned!r} is not shadow/harness (live trading stays off)",
            cleaned,
            client_set,
            token_set,
        )
    if not client_set or not token_set:
        return GateDecision(
            False,
            "CREDENTIALS_MISSING",
            f"{CLIENT_ID_ENV} and {ACCESS_TOKEN_ENV} are required; values are not logged",
            cleaned,
            client_set,
            token_set,
        )
    return GateDecision(True, "OK", "gates passed", cleaned, client_set, token_set)


def require_gates(*, mode: str, env: Mapping[str, str]) -> GateDecision:
    decision = evaluate_gates(mode=mode, env=env)
    if not decision.ok:
        raise HarnessRefused(decision.reason_code, decision.message)
    return decision


def require_transport(transport: str) -> str:
    cleaned = _clean(transport).lower()
    if cleaned not in ALLOWED_TRANSPORTS:
        raise HarnessRefused(
            "TRANSPORT_OFF",
            "transport is off; pass --transport mock|recorded|dhan after gates",
        )
    return cleaned
