"""V2-23 fail-closed founder-command gate. Paper only. No live broker path."""

from __future__ import annotations

from typing import Any

from auth import AuthDecision, authorize_control


def decision_from_raw(raw: Any) -> AuthDecision | None:
    if raw is None:
        return None
    if isinstance(raw, AuthDecision):
        return raw
    if not isinstance(raw, dict):
        return AuthDecision(ok=False, reason="unauthorized")
    return AuthDecision(
        ok=bool(raw.get("ok")),
        role=str(raw.get("role") or ""),
        sub=str(raw.get("sub") or ""),
        typ=str(raw.get("typ") or "access"),
        tfa=bool(raw.get("tfa")),
        reason=str(raw.get("reason") or ""),
        source=str(raw.get("source") or "jwt"),
    )


def authorize_command(
    decision: AuthDecision | None,
    kind: str = "",
    *,
    required: bool = False,
) -> str | None:
    """None = allow. Missing decision is allow unless required (JWT mode)."""
    if decision is None:
        return "unauthorized" if required else None
    return authorize_control(decision, kind)


def refuse_if_auth_present(raw: dict[str, Any]) -> str | None:
    """Engine-side hook. Paper commands without `auth` stay on the V2-11 path."""
    if "auth" not in raw:
        return None
    return authorize_command(decision_from_raw(raw.get("auth")), str(raw.get("kind") or ""), required=True)
