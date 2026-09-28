"""Out-of-band paper flatten: risk.check_flatten then router/exit primitives. No Redis."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from brokers.factory import make_broker  # type: ignore[import-untyped]
from contracts.clock import IST
from contracts.envelope import Envelope


def flatten_paper(
    *,
    account: str,
    clock: Any,
    risk: Any,
    manager: Any,
    underlying: str | None = None,
    reason: str = "out-of-band flatten",
) -> dict[str, Any]:
    """Close paper positions through PositionManager + risk. Never constructs DhanBroker."""
    now: datetime = clock.now().astimezone(IST)
    rd = risk.check_flatten(now=now)
    if not getattr(rd, "approved", False):
        return {
            "ok": False,
            "account": account,
            "reason": getattr(rd, "reason_code", None) or getattr(rd, "reason", "RISK_VETO"),
            "orders": "REFUSED",
        }
    fired: list[str] = []
    open_pos = [p for p in manager.store.open_positions() if str(p.get("account_id") or "founder") == account]
    if underlying:
        open_pos = [p for p in open_pos if str(underlying).upper() in str(p.get("instrument_id") or "").upper()]
    for pos in open_pos:
        iso = now.isoformat(timespec="seconds")
        env = Envelope(
            v=2,
            event_type="FOUNDER_COMMAND",
            event_id="oob-flatten",
            stream="ctl:commands",
            source="runtime.flatten",
            event_ts=iso,
            available_ts=iso,
            timestamp=iso,
            account_id=account,
            correlation_id=None,
            causation_id=None,
            payload={
                "kind": "FLATTEN_ALL",
                "instrument_id": pos.get("instrument_id"),
                "position_id": pos.get("position_id"),
                "why": reason,
            },
        )
        for req in manager.on_market(env):
            fired.append(req.reason)
    return {"ok": True, "account": account, "exits": fired, "why": reason, "orders": "EXIT_ONLY"}


def paper_broker(clock: Any) -> Any:
    """Factory wrapper so callers never import a live broker."""
    return make_broker(mode="paper", clock=clock)
