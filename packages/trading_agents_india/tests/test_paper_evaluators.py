"""PAPER evaluator bind — honest available vs unbound; KEEP_ALL."""

from __future__ import annotations

from trading_agents_india.candidate_audit import (
    CATALOG_CANDIDATES,
    build_candidate_observations,
)
from trading_agents_india.paper_evaluators import (
    BARS_MISSING_DI,
    UNBOUND_AGGREGATE_DI,
    bound_candidate_ids,
    evaluate_candidate,
    unbound_candidate_ids,
)
from trading_agents_india.schemas import PaperTicket


def _ticket(**kwargs) -> PaperTicket:
    base = dict(
        underlying="NIFTY",
        lean="BUY_CE",
        stage="EARLY",
        reasons=["input_mix:MIX-DEFAULT-BUY"],
        risk_veto=False,
        vetoes=[],
        session_kind="NORMAL",
        default_mix_cited="MIX-DEFAULT-BUY",
        confidence=0.4,
        data_gaps=[],
    )
    base.update(kwargs)
    return PaperTicket(**base)  # type: ignore[arg-type]


def test_bound_and_unbound_ids_cover_catalog() -> None:
    bound = set(bound_candidate_ids())
    unbound = set(unbound_candidate_ids())
    assert bound.isdisjoint(unbound)
    assert "MIX-DEFAULT-BUY" in bound
    assert "STRAT-003" in bound
    assert "STRAT-001" in bound
    assert "STRAT-006" in bound
    assert "STRAT-004" in unbound
    assert "STRAT-010" in unbound
    assert "STRAT-013" in unbound
    for cid in CATALOG_CANDIDATES:
        assert cid in bound or cid in unbound


def test_unbound_share_single_aggregated_di() -> None:
    ticket = _ticket()
    reasons = set()
    for cid in unbound_candidate_ids():
        result = evaluate_candidate(cid, ticket)
        assert result.available is False
        assert result.outcome == "DATA_INSUFFICIENT"
        assert result.data_gaps == [UNBOUND_AGGREGATE_DI]
        reasons.update(result.data_gaps)
    assert reasons == {UNBOUND_AGGREGATE_DI}


def test_strat_003_inherits_default_mix_lean() -> None:
    ticket = _ticket(lean="BUY_CE", risk_veto=False)
    result = evaluate_candidate("STRAT-003", ticket)
    assert result.available is True
    assert result.raw_lean == "BUY_CE"
    assert result.outcome == "BUY_CE"


def test_strat_003_veto_mirrors_ticket() -> None:
    ticket = _ticket(
        lean="HOLD",
        stage="VETOED",
        risk_veto=True,
        vetoes=["MIX-CLOCK-CAS dead-band"],
        reasons=["MIX-CLOCK-CAS dead-band"],
    )
    result = evaluate_candidate("STRAT-003", ticket)
    assert result.available is True
    assert result.outcome == "VETOED"
    assert result.final_lean == "HOLD"


def test_strat_001_bound_but_bars_missing() -> None:
    result = evaluate_candidate("STRAT-001", _ticket())
    assert result.available is True
    assert result.outcome == "DATA_INSUFFICIENT"
    assert BARS_MISSING_DI in result.data_gaps


def test_clock_filter_fires_on_dead_band() -> None:
    ticket = _ticket(
        lean="HOLD",
        stage="VETOED",
        risk_veto=True,
        vetoes=["MIX-CLOCK-CAS dead-band"],
        reasons=["dead-band"],
    )
    result = evaluate_candidate("STRAT-007", ticket)
    assert result.available is True
    assert result.outcome == "VETOED"


def test_event_hold_allow_when_quiet() -> None:
    result = evaluate_candidate("MIX-TA-EVENT-HOLD", _ticket())
    assert result.available is True
    assert result.outcome == "ALLOW"


def test_build_observations_provenance_flags() -> None:
    rows = build_candidate_observations(
        _ticket(risk_veto=True, lean="HOLD", stage="VETOED", vetoes=["BIG_NEWS: hold"]),
        as_of_ist="2026-09-07T12:00:00+05:30",
        tick_index=0,
    )
    assert len(rows) == len(CATALOG_CANDIDATES)
    by_id = {r.candidate_id: r for r in rows}
    assert by_id["MIX-DEFAULT-BUY"].provenance["candidate_evaluator_available"] is True
    assert by_id["STRAT-004"].provenance["candidate_evaluator_available"] is False
    assert by_id["STRAT-004"].data_gaps == [UNBOUND_AGGREGATE_DI]
    assert by_id["STRAT-001"].provenance["candidate_evaluator_available"] is True
    assert by_id["STRAT-001"].outcome == "DATA_INSUFFICIENT"
    # Unbound stubs list the shared unbound id set once in provenance
    assert "STRAT-014" in by_id["STRAT-004"].provenance["unbound_evaluator_ids"]
    # Okala-IN bound (FOUNDER_PAPER_ACCEPT) — news soft-default does not VETO
    assert by_id["MIX-CF-OKALA-IN-H-CROSS"].provenance["candidate_evaluator_available"] is True
    # Without bars → DI; news alone must not force VETOED when NEWS_VETO_ENABLED=false
    assert by_id["MIX-CF-OKALA-IN-H-CROSS"].outcome in ("DATA_INSUFFICIENT", "WATCH")
    assert by_id["MIX-CF-OKALA-IN-H-CROSS"].outcome != "VETOED"
    assert by_id["MIX-TA-EVENT-HOLD"].outcome == "ALLOW"

def test_okala_in_bound_not_unbound_di() -> None:
    assert "MIX-CF-OKALA-IN-H-CROSS" in bound_candidate_ids()
    result = evaluate_candidate("MIX-CF-OKALA-IN-H-CROSS", _ticket())
    assert result.available is True
    assert result.outcome == "DATA_INSUFFICIENT"
    assert any("Okala-IN" in g or "okala" in g.lower() for g in result.data_gaps)
    assert result.provenance_extra.get("founder_label") == "FOUNDER_PAPER_ACCEPT"
    assert result.provenance_extra.get("NO_PROMOTE") is True


def test_okala_in_big_news_veto_only_when_enabled(monkeypatch) -> None:
    ticket = _ticket(
        lean="HOLD",
        stage="VETOED",
        risk_veto=True,
        vetoes=["BIG_NEWS: hold customer ticket"],
        session_kind="NEWS_DAY",
        top_veto_reasons=["BIG_NEWS hold"],
    )
    # Soft-default: news does not veto Okala
    monkeypatch.delenv("NEWS_VETO_ENABLED", raising=False)
    result = evaluate_candidate("MIX-CF-OKALA-IN-REPAIR", ticket)
    assert result.available is True
    assert result.outcome != "VETOED"

    monkeypatch.setenv("NEWS_VETO_ENABLED", "true")
    result_on = evaluate_candidate("MIX-CF-OKALA-IN-REPAIR", ticket)
    assert result_on.available is True
    assert result_on.outcome == "VETOED"
    assert result_on.final_lean == "HOLD"