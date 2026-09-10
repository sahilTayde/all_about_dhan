"""PAPER-only audit adapter for the KEEP_ALL candidate catalog.

Builds one observation per catalog STRAT/MIX. Bound evaluators come from
``paper_evaluators`` (reuse ticket + filter roles + backtest_engine refs).
Unbound PARKED/WAITING rows share one aggregated DI reason — no silent fake
leans, no catalog deletes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Optional

from trading_agents_india.paper_evaluators import (
    EVALUATOR_BINDS,
    UNBOUND_AGGREGATE_DI,
    evaluate_candidate,
    unbound_candidate_ids,
)
from trading_agents_india.schemas import PaperTicket

CATALOG_CANDIDATES: tuple[str, ...] = tuple(
    [f"STRAT-{i:03d}" for i in range(1, 15)]
    + [
        "MIX-DEFAULT-BUY",
        "MIX-TA-FLOW-RISK",
        "MIX-TA-EVENT-HOLD",
        "MIX-TA-EXEC-SANITY",
        "MIX-TA-MARKET-HOURS",
        "MIX-LEAN-SPOT-ATM",
        "MIX-IMPULSE-1M",
        "MIX-003-INDEX-PROXY",
        "MIX-006-INDEX-PROXY",
        "MIX-PCR-EXTREME-HOLD",
        "MIX-SELL-CREDIT-PARK",
    ]
)

# Scoring collapse id — not STRAT-015+. KEEP_ALL parked IDs live in provenance.
KEEP_ALL_UNBOUND_DI = "KEEP_ALL-UNBOUND-DI"


def working_score_ids(catalog: Iterable[str] = CATALOG_CANDIDATES) -> list[str]:
    """PAPER tick scoring list: bound evaluators only (customer updates)."""
    out: list[str] = []
    for cid in catalog:
        bind = EVALUATOR_BINDS.get(cid)
        if bind is not None and bind.available:
            out.append(cid)
    return out


def parked_score_ids(catalog: Iterable[str] = CATALOG_CANDIDATES) -> list[str]:
    working = set(working_score_ids(catalog))
    return [cid for cid in catalog if cid not in working]


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
    bars: Optional[list[Any]] = None,
    collapse_parked: bool = True,
) -> list[CandidateObservation]:
    """Score working-path candidates; collapse PARKED/WAITING KEEP_ALL into one DI row.

    IDs are not deleted. ``collapse_parked=False`` emits one row per catalog id
    (KEEP_ALL audit). Default PAPER ticks collapse so unbound DI does not drown
    MIX-DEFAULT-BUY / Okala-IN / clock filters.
    """
    catalog = tuple(candidate_ids)
    rows: list[CandidateObservation] = []
    unbound = unbound_candidate_ids()
    working = working_score_ids(catalog) if collapse_parked else list(catalog)
    parked = parked_score_ids(catalog) if collapse_parked else []

    def _row(candidate_id: str) -> CandidateObservation:
        bind = EVALUATOR_BINDS.get(candidate_id)
        timeframe = bind.timeframe if bind else "UNSUPPORTED"
        result = evaluate_candidate(candidate_id, ticket, bars=bars)
        gaps = list(dict.fromkeys(result.data_gaps))
        components = _components(ticket, available=result.available)
        return CandidateObservation(
            observation_id=f"{as_of_ist}:{tick_index}:{ticket.underlying}:{candidate_id}",
            candidate_id=candidate_id,
            strategy_or_mix_id=candidate_id,
            underlying=ticket.underlying,
            timeframe=timeframe,
            source=source,
            provenance={
                **ticket.provenance,
                "catalog_adapter": "paper_evaluators_v1",
                "candidate_evaluator_available": result.available,
                "unbound_evaluator_ids": unbound if not result.available else [],
                **result.provenance_extra,
            },
            as_of_ist=as_of_ist,
            freshness={
                "status": "STALE" if ticket.data_gaps else "FRESHNESS_UNKNOWN",
                "data_gaps": gaps,
            },
            raw_lean=result.raw_lean,
            final_lean=result.final_lean,
            outcome=result.outcome,
            vetoes=list(result.vetoes),
            confidence_components=components,
            confidence=_confidence(components),
            data_gaps=gaps,
            status=(bind.catalog_status if bind else "UNVALIDATED"),
        )

    for candidate_id in working:
        rows.append(_row(candidate_id))

    if collapse_parked and parked:
        components = _components(ticket, available=False)
        rows.append(
            CandidateObservation(
                observation_id=f"{as_of_ist}:{tick_index}:{ticket.underlying}:{KEEP_ALL_UNBOUND_DI}",
                candidate_id=KEEP_ALL_UNBOUND_DI,
                strategy_or_mix_id=KEEP_ALL_UNBOUND_DI,
                underlying=ticket.underlying,
                timeframe="collapsed",
                source=source,
                provenance={
                    **ticket.provenance,
                    "catalog_adapter": "paper_evaluators_v1",
                    "candidate_evaluator_available": False,
                    "unbound_evaluator_ids": list(parked),
                    "keep_all": True,
                    "collapse_di": True,
                    "bind_kind": "collapsed_parked",
                    "catalog_status": "PARKED",
                },
                as_of_ist=as_of_ist,
                freshness={
                    "status": "STALE" if ticket.data_gaps else "FRESHNESS_UNKNOWN",
                    "data_gaps": [UNBOUND_AGGREGATE_DI],
                },
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="DATA_INSUFFICIENT",
                vetoes=[],
                confidence_components=components,
                confidence=_confidence(components),
                data_gaps=[UNBOUND_AGGREGATE_DI],
                status="PARKED",
            )
        )
    return rows
