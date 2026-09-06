"""Structured paper-signal schemas for the India agent loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional  # Mode used on SessionResult

Lean = Literal["BUY_CE", "BUY_PE", "HOLD"]
Stage = Literal["WATCH", "EARLY", "VETOED"]
SessionKind = Literal["NORMAL", "NEWS_DAY", "EXPIRY"]
Layer = Literal["SOURCE_FACT", "VALIDATION", "HYPOTHESIS"]
Underlying = Literal["NIFTY", "BANKNIFTY", "SENSEX"]
Mode = Literal["PAPER", "LIVE"]


@dataclass
class AgentReport:
    role: str
    summary: str
    lean_hint: Lean = "HOLD"
    confidence: float = 0.0
    layer: Layer = "HYPOTHESIS"
    citations: list[str] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)
    used_llm: bool = False
    trading_agents_name: str = ""
    india_role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTicket:
    underlying: Underlying
    lean: Lean
    stage: Stage
    reasons: list[str]
    risk_veto: bool
    vetoes: list[str]
    session_kind: SessionKind
    default_mix_cited: str = "MIX-DEFAULT-BUY"
    layer: Layer = "HYPOTHESIS"
    execution: str = "refused"
    confidence: float = 0.0
    data_gaps: list[str] = field(default_factory=list)
    bull_summary: str = ""
    bear_summary: str = ""
    news_summary: str = ""
    sentiment_summary: str = ""
    technical_summary: str = ""
    chain_watcher_summary: str = ""
    risk_summary: str = ""
    boss_summary: str = ""
    trader_summary: str = ""
    premium_lean: dict[str, Any] = field(default_factory=dict)
    reports: list[dict[str, Any]] = field(default_factory=list)
    handoffs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SessionResult:
    as_of_ist: str
    mode: Mode
    openai_used: bool
    openai_key_present: bool
    tickets: list[PaperTicket]
    compliance: str
    external_ref: str = (
        "https://github.com/TauricResearch/TradingAgents (Apache-2.0)"
    )
    kb_path: Optional[str] = None
    data_gaps: list[str] = field(default_factory=list)
    live_gate: dict[str, Any] = field(default_factory=dict)
    live_order_attempt: Optional[dict[str, Any]] = None
    personas_cited: list[dict[str, Any]] = field(default_factory=list)
    handoffs: list[dict[str, Any]] = field(default_factory=list)
    clock: dict[str, Any] = field(default_factory=dict)
    mix_inputs: dict[str, Any] = field(default_factory=dict)
    paper_watch_mixes: list[str] = field(
        default_factory=lambda: [
            "MIX-DEFAULT-BUY",
            "MIX-TA-FLOW-RISK",
            "MIX-TA-EVENT-HOLD",
            "MIX-TA-EXEC-SANITY",
            "MIX-TA-MARKET-HOURS",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of_ist": self.as_of_ist,
            "mode": self.mode,
            "openai_used": self.openai_used,
            "openai_key_present": self.openai_key_present,
            "tickets": [t.to_dict() for t in self.tickets],
            "compliance": self.compliance,
            "external_ref": self.external_ref,
            "kb_path": self.kb_path,
            "data_gaps": self.data_gaps,
            "live_gate": self.live_gate,
            "live_order_attempt": self.live_order_attempt,
            "personas_cited": self.personas_cited,
            "handoffs": self.handoffs,
            "clock": self.clock,
            "mix_inputs": self.mix_inputs,
            "paper_watch_mixes": self.paper_watch_mixes,
            "execution": "refused",
            "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        }
