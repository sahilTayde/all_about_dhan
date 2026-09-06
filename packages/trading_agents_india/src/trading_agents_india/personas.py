"""TradingAgents persona aliases → India desk roles.

EXTERNAL: TauricResearch/TradingAgents (Apache-2.0).
Maps upstream display names onto our sequential pipeline roles and teams/00–09.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Persona:
    trading_agents_name: str
    pipeline_role: str
    india_role: str
    our_team: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Canonical registry (SOURCE_FACT of mapping intent; runtime still HYPOTHESIS).
PERSONAS: tuple[Persona, ...] = (
    Persona(
        trading_agents_name="News Analyst",
        pipeline_role="news_analyst",
        india_role="India Event / News Filter",
        our_team="05",
        notes="Hold overlay via desk_intel Moneycontrol RSS; Dhan news DI if no API",
    ),
    Persona(
        trading_agents_name="Sentiment Analyst",
        pipeline_role="sentiment_analyst",
        india_role="India Sentiment (DI until wired)",
        our_team="05",
        notes="No StockTwits/Reddit as SOURCE_FACT",
    ),
    Persona(
        trading_agents_name="Market Analyst",
        pipeline_role="technical_analyst",
        india_role="Index Regime / Chain Lean Analyst",
        our_team="04",
        notes="5m ST/MACD/RSI confirm-or-kill only",
    ),
    Persona(
        trading_agents_name="Fundamentals Analyst",
        pipeline_role="fundamentals_skipped",
        india_role="Macro / Policy Context (CAS note only)",
        our_team="03",
        notes="SKIP equity filings as NIFTY alpha; CAS-* pointer only",
    ),
    Persona(
        trading_agents_name="Bull Researcher",
        pipeline_role="bull_researcher",
        india_role="CE Case Challenger",
        our_team="02/04",
        notes="Peer challenge; never catalog delete",
    ),
    Persona(
        trading_agents_name="Bear Researcher",
        pipeline_role="bear_researcher",
        india_role="PE / Hold Case Challenger",
        our_team="02/04",
        notes="Peer challenge; never catalog delete",
    ),
    Persona(
        trading_agents_name="Research Manager",
        pipeline_role="boss_research_manager",
        india_role="Boss Desk Synthesizer",
        our_team="00",
        notes="BOSS_AGENT mandate; cites MIX-DEFAULT-BUY",
    ),
    Persona(
        trading_agents_name="Portfolio Manager",
        pipeline_role="boss_research_manager",
        india_role="00 Final Paper Ticket Call",
        our_team="00",
        notes="Same boss node in v0; catalog untouched",
    ),
    Persona(
        trading_agents_name="Trader",
        pipeline_role="trader",
        india_role="Paper Execution Coordinator",
        our_team="07/08",
        notes="BUY_CE|BUY_PE|HOLD paper lean; execution refused",
    ),
    Persona(
        trading_agents_name="Aggressive Risk Debator",
        pipeline_role="risk_committee",
        india_role="Premium Risk — Aggressive Hat",
        our_team="06",
        notes="Collapsed into risk_committee v0; may not force size",
    ),
    Persona(
        trading_agents_name="Conservative Risk Debator",
        pipeline_role="risk_committee",
        india_role="Premium Risk — Conservative Hat",
        our_team="06",
        notes="Caps confidence; NEWS_DAY veto",
    ),
    Persona(
        trading_agents_name="Neutral Risk Debator",
        pipeline_role="risk_committee",
        india_role="Premium Risk — Neutral Hat",
        our_team="06",
        notes="No-edge → HOLD / WATCH",
    ),
    Persona(
        trading_agents_name="Risk Manager",
        pipeline_role="risk_committee",
        india_role="Premium Risk & Loss Gate",
        our_team="06",
        notes="Umbrella for risk triad",
    ),
)


_BY_PIPELINE: dict[str, list[Persona]] = {}
_BY_TA_NAME: dict[str, Persona] = {}
for _p in PERSONAS:
    _BY_PIPELINE.setdefault(_p.pipeline_role, []).append(_p)
    _BY_TA_NAME[_p.trading_agents_name.lower()] = _p


def resolve_by_pipeline_role(role: str) -> Optional[Persona]:
    rows = _BY_PIPELINE.get(role) or []
    return rows[0] if rows else None


def resolve_by_trading_agents_name(name: str) -> Optional[Persona]:
    return _BY_TA_NAME.get((name or "").strip().lower())


def registry_payload() -> list[dict[str, Any]]:
    return [p.to_dict() for p in PERSONAS]


def display_label(pipeline_role: str) -> str:
    p = resolve_by_pipeline_role(pipeline_role)
    if not p:
        return pipeline_role
    return f"{p.trading_agents_name} / {p.india_role}"
