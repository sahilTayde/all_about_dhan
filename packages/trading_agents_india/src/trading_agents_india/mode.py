"""PAPER vs LIVE mode gate. LIVE always refuses broker orders for now.

Future live path is DhanHQ-only (never invent brokers). Founder allow + gate
flags exist as stubs; until both are true AND SafeMode is lifted in
dhan_client, LIVE still refuses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

Mode = Literal["PAPER", "LIVE"]


@dataclass(frozen=True)
class LiveGateStatus:
    mode: Mode
    orders_allowed: bool
    broker: str = "dhanhq"
    reasons: list[str] = field(default_factory=list)
    founder_allow: bool = False
    live_gate_env: bool = False
    research_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "orders_allowed": self.orders_allowed,
            "broker": self.broker,
            "reasons": list(self.reasons),
            "founder_allow": self.founder_allow,
            "live_gate_env": self.live_gate_env,
            "research_ready": self.research_ready,
            "execution": "refused" if not self.orders_allowed else "UNKNOWN",
        }


def normalize_mode(raw: Optional[str], *, default: Mode = "PAPER") -> Mode:
    text = (raw or default).strip().upper()
    if text in ("PAPER", "DRY-RUN", "DRY_RUN", "DRYRUN"):
        return "PAPER"
    if text == "LIVE":
        return "LIVE"
    return default


def _env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes", "on")


def evaluate_live_gate(mode: Mode) -> LiveGateStatus:
    """Return whether orders would be allowed. Today: never for LIVE or PAPER.

    PAPER: paper ledger only — no broker orders.
    LIVE: refuses unless (and even then we hard-refuse in this package until
    product gate) founder allow + env gate + RESEARCH_READY. Currently all
    three are false by default → refuse.
    """
    founder = _env_truthy("TRADING_AGENTS_FOUNDER_ALLOW_LIVE")
    gate = _env_truthy("TRADING_AGENTS_LIVE_GATE")
    # Product gate is not set in this workspace; do not invent it.
    research_ready = False

    reasons: list[str] = []
    if mode == "PAPER":
        reasons.append("mode=PAPER: paper ledger only; broker orders refused")
        return LiveGateStatus(
            mode="PAPER",
            orders_allowed=False,
            reasons=reasons,
            founder_allow=founder,
            live_gate_env=gate,
            research_ready=research_ready,
        )

    # mode == LIVE
    reasons.append("mode=LIVE requested")
    reasons.append("broker_path=dhanhq_only (stub; no other brokers)")
    if not founder:
        reasons.append(
            "REFUSED: TRADING_AGENTS_FOUNDER_ALLOW_LIVE not set (default refuse)"
        )
    if not gate:
        reasons.append("REFUSED: TRADING_AGENTS_LIVE_GATE not set (default refuse)")
    if not research_ready:
        reasons.append(
            "REFUSED: RESEARCH_READY_FOR_PROGRAMMING not earned — hard refuse"
        )
    reasons.append(
        "REFUSED: trading_agents_india never places live orders in this pass; "
        "use dhan_client.ExecutionClient which also refuses"
    )
    return LiveGateStatus(
        mode="LIVE",
        orders_allowed=False,  # hard refuse for now even if flags were true
        reasons=reasons,
        founder_allow=founder,
        live_gate_env=gate,
        research_ready=research_ready,
    )


def attempt_live_order(*, mode: Mode, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Future DhanHQ live seam. Always returns refused structured response."""
    status = evaluate_live_gate(mode)
    out: dict[str, Any] = {
        "ok": False,
        "execution": "refused",
        "broker": "dhanhq",
        "mode": status.mode,
        "gate": status.to_dict(),
        "payload_echo_keys": sorted((payload or {}).keys()),
        "suggestion": "Run mode=PAPER session; log lean to trading_agents_india.sqlite",
    }
    # Optional: call dhan ExecutionClient to prove refuse (no secrets logged).
    try:
        from dhan_client.execution import ExecutionClient  # type: ignore

        try:
            ExecutionClient().place_order(**(payload or {}))
        except Exception as exc:  # noqa: BLE001
            out["dhan_execution_client"] = {
                "called": True,
                "refused": True,
                "error_type": type(exc).__name__,
            }
    except Exception:
        out["dhan_execution_client"] = {
            "called": False,
            "note": "DATA_INSUFFICIENT: dhan_client not importable in this env",
        }
    return out
