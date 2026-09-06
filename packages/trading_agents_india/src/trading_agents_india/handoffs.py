"""Structured agent-to-agent handoff messages (TradingAgents-inspired).

Trader emits paper CE/PE/HOLD only; execution always refused.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from trading_agents_india.schemas import AgentReport, Layer, Lean


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
    execution: str = "refused"
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
