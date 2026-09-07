"""PAPER-only audit adapter for the KEEP_ALL candidate catalog.

The current agent graph evaluates one aggregate paper ticket.  This adapter
does not invent per-strategy signals: the configured default mix is the only
candidate with an available evaluator, while every other catalog row is
preserved as DATA_INSUFFICIENT with its explicit reason.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from trading_agents_india.schemas import PaperTicket

CATALOG_CANDIDATES: tuple[str, ...] = tuple(
    [f"STRAT-{i:03d}" for i in range(1, 15)]
    + [
        "MIX-DEFAULT-BUY",
        "MIX-TA-FLOW-RISK",
        "MIX-TA-EVENT-HOLD",
        "MIX-TA-EXEC-SANITY",
        "MIX-TA-MARKET-HOURS",
    ]
)

_TIMEFRAMES = {
    "STRAT-003": "3m",
    "STRAT-006": "2m",
    "STRAT-007": "session-filter",
    "STRAT-009": "session-filter",
    "STRAT-010": "futures-tape",
    "MIX-DEFAULT-BUY": "aggregate",
    "MIX-TA-FLOW-RISK": "aggregate",
    "MIX-TA-EVENT-HOLD": "aggregate",
    "MIX-TA-EXEC-SANITY": "aggregate",
    "MIX-TA-MARKET-HOURS": "aggregate",
}


@dataclass(frozen=True)
class CandidateObservation:
    """One append-only candidate observation; never a fill or win-rate row."""

    observation_id: str
    candidate_id: str
    strategy_or_mix_id: str
    underlying: str
    timeframe: str
    source: str
    provenance: dict[str, Any]
    as_of_ist: str
    freshness: dict[str, Any]
    raw_lean: str
    final_lean: str
    outcome: str
    vetoes: list[str] = field(default_factory=list)
    confidence_components: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    execution: str = "refused"
    data_gaps: list[str] = field(default_factory=list)
    status: str = "UNVALIDATED"
    promote: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _components(ticket: PaperTicket, *, available: bool) -> dict[str, float]:
    """Bounded data/consensus quality components, explicitly not win rate."""
    if not available:
        return {
            "data_quality": 0.0,
            "consensus_quality": 0.0,
            "freshness_quality": 0.0,
            "veto_penalty": 0.0,
        }
    data_quality = 0.0 if ticket.data_gaps else 1.0
    consensus_quality = min(1.0, max(0.0, float(ticket.confidence)))
    freshness_quality = 0.0 if ticket.data_gaps else 1.0
    veto_penalty = 1.0 if ticket.risk_veto else 0.0
    return {
        "data_quality": data_quality,
        "consensus_quality": consensus_quality,
        "freshness_quality": freshness_quality,
        "veto_penalty": veto_penalty,
    }


def _confidence(components: dict[str, float]) -> float:
    score = (
        components["data_quality"] * 0.4
        + components["consensus_quality"] * 0.4
        + components["freshness_quality"] * 0.2
        - components["veto_penalty"] * 0.2
    )
    return round(min(1.0, max(0.0, score)), 4)


def build_candidate_observations(
    ticket: PaperTicket,
    *,
    as_of_ist: str,
    tick_index: int,
    source: str = "trading_agents_india.catalog_adapter",
    candidate_ids: Iterable[str] = CATALOG_CANDIDATES,
) -> list[CandidateObservation]:
    """Build one record for every known candidate without silent omission."""
    rows: list[CandidateObservation] = []
    for candidate_id in candidate_ids:
        available = candidate_id == ticket.default_mix_cited
        timeframe = _TIMEFRAMES.get(candidate_id, "UNSUPPORTED")
        gaps = list(ticket.data_gaps)
        vetoes = list(ticket.vetoes)
        raw_lean = ticket.lean if available else "HOLD"
        final_lean = raw_lean
        if not available:
            gaps.append(
                f"DATA_INSUFFICIENT: no PAPER evaluator bound for {candidate_id}"
            )
            outcome = "DATA_INSUFFICIENT"
        elif ticket.risk_veto:
            outcome = "VETOED"
        elif ticket.data_gaps:
            outcome = "STALE"
        else:
            outcome = final_lean
        gaps = list(dict.fromkeys(gaps))
        components = _components(ticket, available=available)
        rows.append(
            CandidateObservation(
                observation_id=f"{as_of_ist}:{tick_index}:{ticket.underlying}:{candidate_id}",
                candidate_id=candidate_id,
                strategy_or_mix_id=candidate_id,
                underlying=ticket.underlying,
                timeframe=timeframe,
                source=source,
                provenance={
                    **ticket.provenance,
                    "catalog_adapter": "fixture_or_bound_aggregate",
                    "candidate_evaluator_available": available,
                },
                as_of_ist=as_of_ist,
                freshness={
                    "status": "STALE" if ticket.data_gaps else "FRESHNESS_UNKNOWN",
                    "data_gaps": gaps,
                },
                raw_lean=raw_lean,
                final_lean=final_lean,
                outcome=outcome,
                vetoes=vetoes,
                confidence_components=components,
                confidence=_confidence(components),
                data_gaps=gaps,
            )
        )
    return rows
