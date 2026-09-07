"""Structured agent-to-agent handoff messages (TradingAgents-inspired).

Trader emits paper CE/PE/HOLD only; execution always refused.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from trading_agents_india.schemas import AgentReport, Layer, Lean

ALLOWED_LEANS = {"BUY_CE", "BUY_PE", "HOLD"}
FORBIDDEN_PAYLOAD_KEYS = {
    "lots",
    "quantity_lots",
    "enable_execution",
    "live_orders",
    "promote",
    "research_ready",
}


@dataclass
class AgentHandoff:
    from_role: str
    to_role: str
    lean_hint: Lean
    summary: str
    layer: Layer = "HYPOTHESIS"
    citations: list[str] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)
    confidence: float = 0.0
    trading_agents_name: str = ""
    india_role: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    execution: str = "refused"
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_handoff(handoff: AgentHandoff) -> list[str]:
    """Return deterministic schema/policy violations for one handoff."""
    errors: list[str] = []
    if not handoff.from_role or not handoff.to_role:
        errors.append("MALFORMED_PAYLOAD: handoff roles are required")
    if handoff.lean_hint not in ALLOWED_LEANS:
        errors.append("MALFORMED_PAYLOAD: invalid lean")
    if not 0 <= float(handoff.confidence) <= 1:
        errors.append("MALFORMED_PAYLOAD: confidence outside 0..1")
    if handoff.execution != "refused":
        errors.append("POLICY_VETO: handoff execution must remain refused")
    if not handoff.provenance or not handoff.provenance.get("source"):
        errors.append("MALFORMED_PAYLOAD: provenance.source required")
    if any(key in handoff.payload for key in FORBIDDEN_PAYLOAD_KEYS):
        errors.append("POLICY_VETO: payload cannot alter lots, execution, or promotion")
    if handoff.from_role == "trader" and handoff.payload.get("paper_only") is not True:
        errors.append("POLICY_VETO: trader handoff must be paper_only")
    return errors


def validate_handoff_chain(handoffs: list[AgentHandoff]) -> list[str]:
    errors: list[str] = []
    for handoff in handoffs:
        errors.extend(validate_handoff(handoff))
    return list(dict.fromkeys(errors))


# Canonical sequential graph (India paper desk).
HANDOFF_GRAPH: tuple[tuple[str, str], ...] = (
    ("news_analyst", "sentiment_analyst"),
    ("sentiment_analyst", "technical_analyst"),
    ("technical_analyst", "chain_watcher"),
    ("chain_watcher", "bull_researcher"),
    ("bull_researcher", "bear_researcher"),
    ("bear_researcher", "boss_research_manager"),
    ("boss_research_manager", "trader"),
    ("trader", "risk_committee"),
)


def handoff_from_report(
    report: AgentReport,
    *,
    to_role: str,
    extra_payload: Optional[dict[str, Any]] = None,
) -> AgentHandoff:
    return AgentHandoff(
        from_role=report.role,
        to_role=to_role,
        lean_hint=report.lean_hint,
        summary=report.summary[:500],
        layer=report.layer,
        citations=list(report.citations),
        data_gaps=list(report.data_gaps),
        confidence=float(report.confidence),
        trading_agents_name=report.trading_agents_name,
        india_role=report.india_role,
        provenance=dict(report.provenance),
        execution="refused",
        payload=dict(extra_payload or {}),
    )


def build_handoff_chain(reports: list[AgentReport]) -> list[AgentHandoff]:
    """Wire sequential handoffs from completed reports; missing edges skipped."""
    by_role = {r.role: r for r in reports}
    out: list[AgentHandoff] = []
    for frm, to in HANDOFF_GRAPH:
        src = by_role.get(frm)
        if src is None:
            continue
        payload: dict[str, Any] = {}
        if frm == "trader":
            payload["paper_only"] = True
            payload["allowed_leans"] = ["BUY_CE", "BUY_PE", "HOLD"]
            payload["live_orders"] = "refused"
        out.append(handoff_from_report(src, to_role=to, extra_payload=payload))
    return out
