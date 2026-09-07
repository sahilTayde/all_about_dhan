"""PAPER catalog evaluator bind — honest available vs stub, KEEP_ALL intact.

Bound evaluators reuse ticket state + known backtest_engine / filter roles.
Unbound PARKED/WAITING/NOT_CODED rows share one aggregated DI reason (no UI soup).
Never invent CE/PE leans without bars. No orders. No promote.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from trading_agents_india.schemas import PaperTicket

# Single aggregated DI for all unbound stubs — do not explode per-STRAT prose in UI.
UNBOUND_AGGREGATE_DI = (
    "DATA_INSUFFICIENT: PAPER evaluator unbound "
    "(PARKED/WAITING/NOT_CODED/overlay-incomplete); KEEP_ALL — not deleted"
)

BARS_MISSING_DI = (
    "DATA_INSUFFICIENT: evaluator bound in backtest_engine but INDEX/FUTIDX bars "
    "not attached to this PAPER agent tick — refusing fake lean"
)


@dataclass(frozen=True)
class EvaluatorBind:
    """Declarative bind status for one catalog candidate."""

    candidate_id: str
    available: bool
    bind_kind: str
    catalog_status: str
    timeframe: str
    layer: str
    module: str
    reason: str


# Registry: STRAT-001–014 + named MIX rows already in candidate_audit catalog.
EVALUATOR_BINDS: dict[str, EvaluatorBind] = {
    "MIX-DEFAULT-BUY": EvaluatorBind(
        candidate_id="MIX-DEFAULT-BUY",
        available=True,
        bind_kind="aggregate_ticket",
        catalog_status="PAPER_DEFAULT",
        timeframe="aggregate",
        layer="HYPOTHESIS",
        module="trading_agents_india.pipeline + backtest_engine.algos.strat_003",
        reason="Customer default MIX; paper ticket lean/veto is the bound evaluator",
    ),
    "MIX-TA-FLOW-RISK": EvaluatorBind(
        candidate_id="MIX-TA-FLOW-RISK",
        available=True,
        bind_kind="paper_watch_mirror",
        catalog_status="PAPER_WATCH",
        timeframe="aggregate",
        layer="HYPOTHESIS",
        module="trading_agents_india.ledger.PAPER_WATCH_MIXES",
        reason="Paper-watch mirror of session ticket (cited in reasons; not a promote)",
    ),
    "MIX-TA-EVENT-HOLD": EvaluatorBind(
        candidate_id="MIX-TA-EVENT-HOLD",
        available=True,
        bind_kind="event_hold_filter",
        catalog_status="PAPER_WATCH",
        timeframe="aggregate",
        layer="HYPOTHESIS",
        module="trading_agents_india.hooks.event_memory",
        reason="Event/news hold filter — mirrors BIG_NEWS / NEWS_DAY vetoes",
    ),
    "MIX-TA-EXEC-SANITY": EvaluatorBind(
        candidate_id="MIX-TA-EXEC-SANITY",
        available=True,
        bind_kind="paper_watch_mirror",
        catalog_status="PAPER_WATCH",
        timeframe="aggregate",
        layer="HYPOTHESIS",
        module="trading_agents_india.ledger.PAPER_WATCH_MIXES",
        reason="Exec-sanity paper-watch mirror (orders always refused)",
    ),
    "MIX-TA-MARKET-HOURS": EvaluatorBind(
        candidate_id="MIX-TA-MARKET-HOURS",
        available=True,
        bind_kind="clock_filter",
        catalog_status="PAPER_WATCH",
        timeframe="session-filter",
        layer="HYPOTHESIS",
        module="trading_agents_india.session_clock",
        reason="Market-hours / dead-band clock filter from ticket vetoes",
    ),
    "STRAT-001": EvaluatorBind(
        candidate_id="STRAT-001",
        available=True,
        bind_kind="algo_needs_bars",
        catalog_status="BACKTEST_BOOK",
        timeframe="60m+5m",
        layer="HYPOTHESIS",
        module="backtest_engine.algos.strat_001_child / run_strat_001",
        reason=BARS_MISSING_DI,
    ),
    "STRAT-002": EvaluatorBind(
        candidate_id="STRAT-002",
        available=True,
        bind_kind="premium_overlay",
        catalog_status="OVERLAY",
        timeframe="option-premium",
        layer="HYPOTHESIS",
        module="backtest_engine.levels.bind_option_premium_levels",
        reason="Premium target overlay (MIX-SLTP-PREM-PCT); not an entry lean",
    ),
    "STRAT-003": EvaluatorBind(
        candidate_id="STRAT-003",
        available=True,
        bind_kind="default_mix_constituent",
        catalog_status="BACKTEST_BOOK",
        timeframe="3m",
        layer="HYPOTHESIS",
        module="backtest_engine.algos.strat_003_leans",
        reason=(
            "Primary of MIX-DEFAULT-BUY — inherits aggregate paper lean when default "
            "mix is cited (HYPOTHESIS proxy; not a separate bar pass on agent tick)"
        ),
    ),
    "STRAT-004": EvaluatorBind(
        candidate_id="STRAT-004",
        available=False,
        bind_kind="stub_parked",
        catalog_status="PARKED",
        timeframe="1m-premium",
        layer="HYPOTHESIS",
        module="NOT_CODED (EMA lengths NOT_IN_EN)",
        reason=UNBOUND_AGGREGATE_DI,
    ),
    "STRAT-005": EvaluatorBind(
        candidate_id="STRAT-005",
        available=False,
        bind_kind="stub_overlay",
        catalog_status="OVERLAY",
        timeframe="strike-overlay",
        layer="HYPOTHESIS",
        module="NOT_CODED (needs option history / greeks)",
        reason=UNBOUND_AGGREGATE_DI,
    ),
    "STRAT-006": EvaluatorBind(
        candidate_id="STRAT-006",
        available=True,
        bind_kind="algo_needs_bars",
        catalog_status="BACKTEST_BOOK",
        timeframe="2m",
        layer="HYPOTHESIS",
        module="backtest_engine.algos.strat_006_leans / run_strat_006",
        reason=BARS_MISSING_DI,
    ),
    "STRAT-007": EvaluatorBind(
        candidate_id="STRAT-007",
        available=True,
        bind_kind="clock_filter",
        catalog_status="FILTER",
        timeframe="session-filter",
        layer="HYPOTHESIS",
        module="backtest_engine.clocks.allow_007",
        reason="HAUS session clock filter — evaluated from ticket veto/reason text",
    ),
    "STRAT-008": EvaluatorBind(
        candidate_id="STRAT-008",
        available=True,
        bind_kind="mixed_index_filter",
        catalog_status="FILTER",
        timeframe="session-filter",
        layer="HYPOTHESIS",
        module="backtest_engine.algos.mixed_index_veto",
        reason="Mixed-index avoid filter — evaluated from ticket veto/reason text",
    ),
    "STRAT-009": EvaluatorBind(
        candidate_id="STRAT-009",
        available=True,
        bind_kind="open_flatten_filter",
        catalog_status="FILTER",
        timeframe="session-filter",
        layer="HYPOTHESIS",
        module="backtest_engine.clocks.skip_open_009 / flatten_009",
        reason="Open-skip + flatten filter — evaluated from ticket veto/reason text",
    ),
    "STRAT-010": EvaluatorBind(
        candidate_id="STRAT-010",
        available=False,
        bind_kind="stub_parked",
        catalog_status="PARKED",
        timeframe="futures-tape",
        layer="DATA_INSUFFICIENT",
        module="NOT_CODED (order-flow history DI)",
        reason=UNBOUND_AGGREGATE_DI,
    ),
    "STRAT-011": EvaluatorBind(
        candidate_id="STRAT-011",
        available=False,
        bind_kind="stub_waiting",
        catalog_status="WAITING",
        timeframe="UNSUPPORTED",
        layer="HYPOTHESIS",
        module="WAITING (reversal alt; not default mix)",
        reason=UNBOUND_AGGREGATE_DI,
    ),
    "STRAT-012": EvaluatorBind(
        candidate_id="STRAT-012",
        available=False,
        bind_kind="stub_waiting",
        catalog_status="WAITING",
        timeframe="UNSUPPORTED",
        layer="HYPOTHESIS",
        module="WAITING (candle overlay detail)",
        reason=UNBOUND_AGGREGATE_DI,
    ),
    "STRAT-013": EvaluatorBind(
        candidate_id="STRAT-013",
        available=False,
        bind_kind="stub_waiting",
        catalog_status="WAITING",
        timeframe="UNSUPPORTED",
        layer="HYPOTHESIS",
        module="WAITING (sell credit — not Phase-1 buy)",
        reason=UNBOUND_AGGREGATE_DI,
    ),
    "STRAT-014": EvaluatorBind(
        candidate_id="STRAT-014",
        available=False,
        bind_kind="stub_waiting",
        catalog_status="WAITING",
        timeframe="UNSUPPORTED",
        layer="HYPOTHESIS",
        module="WAITING (call ratio sell — not Phase-1 buy)",
        reason=UNBOUND_AGGREGATE_DI,
    ),
    "MIX-CF-OKALA-IN-LEVEL": EvaluatorBind(
        candidate_id="MIX-CF-OKALA-IN-LEVEL",
        available=True,
        bind_kind="okala_in_paper",
        catalog_status="PAPER_WATCH",
        timeframe="1m-15m",
        layer="HYPOTHESIS",
        module="backtest_engine.okala_in_paper",
        reason=(
            "FOUNDER_PAPER_ACCEPT starter — robust WR>50% cells only; "
            "PAPER CE/PE notify; NO_PROMOTE live; win_rate claim null"
        ),
    ),
    "MIX-CF-OKALA-IN-FORK": EvaluatorBind(
        candidate_id="MIX-CF-OKALA-IN-FORK",
        available=True,
        bind_kind="okala_in_paper",
        catalog_status="PAPER_WATCH",
        timeframe="1m-15m",
        layer="HYPOTHESIS",
        module="backtest_engine.okala_in_paper",
        reason=(
            "FOUNDER_PAPER_ACCEPT starter — robust WR>50% cells only; "
            "PAPER CE/PE notify; NO_PROMOTE live; win_rate claim null"
        ),
    ),
    "MIX-CF-OKALA-IN-H-CROSS": EvaluatorBind(
        candidate_id="MIX-CF-OKALA-IN-H-CROSS",
        available=True,
        bind_kind="okala_in_paper",
        catalog_status="PAPER_WATCH",
        timeframe="1m-15m",
        layer="HYPOTHESIS",
        module="backtest_engine.okala_in_paper",
        reason=(
            "FOUNDER_PAPER_ACCEPT starter — robust WR>50% cells only; "
            "PAPER CE/PE notify; NO_PROMOTE live; win_rate claim null"
        ),
    ),
    "MIX-CF-OKALA-IN-REPAIR": EvaluatorBind(
        candidate_id="MIX-CF-OKALA-IN-REPAIR",
        available=True,
        bind_kind="okala_in_paper",
        catalog_status="PAPER_WATCH",
        timeframe="1m-15m",
        layer="HYPOTHESIS",
        module="backtest_engine.okala_in_paper",
        reason=(
            "FOUNDER_PAPER_ACCEPT starter — robust WR>50% cells only; "
            "PAPER CE/PE notify; NO_PROMOTE live; win_rate claim null"
        ),
    ),
}


def unbound_candidate_ids() -> list[str]:
    return sorted(k for k, v in EVALUATOR_BINDS.items() if not v.available)


def bound_candidate_ids() -> list[str]:
    return sorted(k for k, v in EVALUATOR_BINDS.items() if v.available)


def _blob(ticket: PaperTicket) -> str:
    parts = list(ticket.vetoes) + list(ticket.reasons) + list(ticket.top_veto_reasons)
    parts += list(ticket.data_gaps)
    return " ".join(str(p) for p in parts).upper()


def _has_any(blob: str, needles: tuple[str, ...]) -> bool:
    return any(n in blob for n in needles)


@dataclass
class EvaluatorResult:
    available: bool
    raw_lean: str
    final_lean: str
    outcome: str
    data_gaps: list[str]
    vetoes: list[str]
    provenance_extra: dict[str, Any]


def evaluate_candidate(
    candidate_id: str,
    ticket: PaperTicket,
    *,
    bars: Optional[list[Any]] = None,
) -> EvaluatorResult:
    """Return lean/VETO/DI for one catalog row. Never invent fills or win rates."""
    bind = EVALUATOR_BINDS.get(candidate_id)
    if bind is None:
        return EvaluatorResult(
            available=False,
            raw_lean="HOLD",
            final_lean="HOLD",
            outcome="DATA_INSUFFICIENT",
            data_gaps=[UNBOUND_AGGREGATE_DI],
            vetoes=[],
            provenance_extra={
                "candidate_evaluator_available": False,
                "bind_kind": "unknown_catalog_row",
                "catalog_status": "UNKNOWN",
                "unbound_evaluator_ids": unbound_candidate_ids(),
            },
        )

    base_prov = {
        "candidate_evaluator_available": bind.available,
        "bind_kind": bind.bind_kind,
        "catalog_status": bind.catalog_status,
        "evaluator_module": bind.module,
        "evaluator_layer": bind.layer,
        "evaluator_reason": bind.reason,
    }

    if not bind.available:
        return EvaluatorResult(
            available=False,
            raw_lean="HOLD",
            final_lean="HOLD",
            outcome="DATA_INSUFFICIENT",
            data_gaps=[UNBOUND_AGGREGATE_DI],
            vetoes=[],
            provenance_extra={
                **base_prov,
                "unbound_evaluator_ids": unbound_candidate_ids(),
            },
        )

    blob = _blob(ticket)
    vetoes = list(ticket.vetoes)

    # --- aggregate / watch mirrors ---
    if bind.bind_kind in ("aggregate_ticket", "paper_watch_mirror"):
        return _from_ticket(ticket, vetoes, base_prov, inherit=True)

    if bind.bind_kind == "default_mix_constituent":
        # STRAT-003 inherits default mix lean only when that mix is cited.
        if ticket.default_mix_cited == "MIX-DEFAULT-BUY":
            return _from_ticket(ticket, vetoes, base_prov, inherit=True)
        gaps = list(ticket.data_gaps) + [
            "DATA_INSUFFICIENT: STRAT-003 bound but default mix is not MIX-DEFAULT-BUY"
        ]
        return EvaluatorResult(
            available=True,
            raw_lean="HOLD",
            final_lean="HOLD",
            outcome="DATA_INSUFFICIENT",
            data_gaps=list(dict.fromkeys(gaps)),
            vetoes=vetoes,
            provenance_extra=base_prov,
        )

    if bind.bind_kind == "algo_needs_bars":
        if bars:
            # Bars attached (future live_signals bridge) — still refuse silent
            # lean here; agent audit does not re-run OHLC algos without an
            # explicit bar adapter payload shape.
            gaps = list(ticket.data_gaps) + [
                "DATA_INSUFFICIENT: bars present but agent audit does not yet "
                f"invoke {bind.module} lean pass — BACKTEST_REQUIRED"
            ]
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="DATA_INSUFFICIENT",
                data_gaps=list(dict.fromkeys(gaps)),
                vetoes=vetoes,
                provenance_extra=base_prov,
            )
        return EvaluatorResult(
            available=True,
            raw_lean="HOLD",
            final_lean="HOLD",
            outcome="DATA_INSUFFICIENT",
            data_gaps=list(dict.fromkeys(list(ticket.data_gaps) + [BARS_MISSING_DI])),
            vetoes=vetoes,
            provenance_extra=base_prov,
        )

    if bind.bind_kind == "premium_overlay":
        # STRAT-002: overlay only — never an entry lean from this evaluator.
        prem = ticket.premium_lean or {}
        gaps = list(ticket.data_gaps)
        if not prem.get("ltp") and not prem.get("ok"):
            gaps.append(
                "DATA_INSUFFICIENT: STRAT-002 premium overlay — option LTP not on ticket"
            )
            outcome = "DATA_INSUFFICIENT"
        else:
            outcome = "OVERLAY"
        return EvaluatorResult(
            available=True,
            raw_lean="HOLD",
            final_lean="HOLD",
            outcome=outcome,
            data_gaps=list(dict.fromkeys(gaps)),
            vetoes=vetoes,
            provenance_extra={**base_prov, "overlay": "MIX-SLTP-PREM-PCT"},
        )

    if bind.bind_kind == "event_hold_filter":
        try:
            from trading_agents_india.hooks.event_memory import news_veto_enabled
        except Exception:  # pragma: no cover
            news_veto_enabled = lambda: False  # type: ignore[assignment, misc]
        if not news_veto_enabled():
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="ALLOW",
                data_gaps=list(ticket.data_gaps),
                vetoes=[],
                provenance_extra={
                    **base_prov,
                    "news_veto_enabled": False,
                    "note": "NEWS_VETO_ENABLED=false — event hold parked",
                },
            )
        fired = ticket.risk_veto and _has_any(
            blob, ("BIG_NEWS", "NEWS_DAY", "EVENT_WINDOW", "PREMARKET")
        )
        if fired:
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="VETOED",
                data_gaps=list(ticket.data_gaps),
                vetoes=vetoes or ["MIX-TA-EVENT-HOLD"],
                provenance_extra=base_prov,
            )
        return EvaluatorResult(
            available=True,
            raw_lean="HOLD",
            final_lean="HOLD",
            outcome="ALLOW",
            data_gaps=list(ticket.data_gaps),
            vetoes=[],
            provenance_extra=base_prov,
        )

    if bind.bind_kind == "clock_filter":
        fired = _has_any(
            blob,
            (
                "MIX-CLOCK",
                "DEAD-BAND",
                "DEAD_BAND",
                "CAS",
                "ALLOW_007",
                "STRAT-007",
                "PAPER_PAUSED",
                "MARKET-HOURS",
                "MARKET_HOURS",
                "OUTSIDE ACTIVE",
            ),
        ) or (
            ticket.risk_veto
            and _has_any(blob, ("CLOCK", "SESSION", "DEAD"))
        )
        if fired:
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="VETOED",
                data_gaps=list(ticket.data_gaps),
                vetoes=vetoes or [candidate_id],
                provenance_extra=base_prov,
            )
        return EvaluatorResult(
            available=True,
            raw_lean="HOLD",
            final_lean="HOLD",
            outcome="ALLOW",
            data_gaps=list(ticket.data_gaps),
            vetoes=[],
            provenance_extra=base_prov,
        )

    if bind.bind_kind == "open_flatten_filter":
        fired = _has_any(
            blob, ("STRAT-009", "OPEN SKIP", "SKIP_OPEN", "FLATTEN", "15:15", "0915")
        )
        if fired:
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="VETOED",
                data_gaps=list(ticket.data_gaps),
                vetoes=vetoes or ["STRAT-009"],
                provenance_extra=base_prov,
            )
        return EvaluatorResult(
            available=True,
            raw_lean="HOLD",
            final_lean="HOLD",
            outcome="ALLOW",
            data_gaps=list(ticket.data_gaps),
            vetoes=[],
            provenance_extra=base_prov,
        )

    if bind.bind_kind == "mixed_index_filter":
        fired = _has_any(
            blob, ("STRAT-008", "MIXED-INDEX", "MIXED_INDEX", "INDEXES DISAGREE", "DISAGREE")
        )
        if fired:
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="VETOED",
                data_gaps=list(ticket.data_gaps),
                vetoes=vetoes or ["STRAT-008"],
                provenance_extra=base_prov,
            )
        return EvaluatorResult(
            available=True,
            raw_lean="HOLD",
            final_lean="HOLD",
            outcome="ALLOW",
            data_gaps=list(ticket.data_gaps),
            vetoes=[],
            provenance_extra=base_prov,
        )

    if bind.bind_kind == "okala_in_paper":
        # FOUNDER_PAPER_ACCEPT — bound, not permanently unbound DI.
        try:
            from trading_agents_india.hooks.event_memory import news_veto_enabled as _nve
        except Exception:  # pragma: no cover
            from backtest_engine.okala_in_paper import news_veto_enabled as _nve

        if (
            _nve()
            and ticket.risk_veto
            and _has_any(blob, ("BIG_NEWS", "NEWS_DAY", "BIG_NEWS_HOLD", "EVENT_WINDOW"))
        ):
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="VETOED",
                data_gaps=list(ticket.data_gaps),
                vetoes=vetoes or ["BIG_NEWS"],
                provenance_extra={
                    **base_prov,
                    "founder_label": "FOUNDER_PAPER_ACCEPT",
                    "NO_PROMOTE": True,
                    "news_veto_enabled": True,
                },
            )
        if not bars:
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="DATA_INSUFFICIENT",
                data_gaps=list(
                    dict.fromkeys(
                        list(ticket.data_gaps)
                        + [
                            "DATA_INSUFFICIENT: Okala-IN paper detector needs INDEX bars "
                            "on this agent tick — refusing fake lean (bound, not unbound)"
                        ]
                    )
                ),
                vetoes=vetoes,
                provenance_extra={
                    **base_prov,
                    "founder_label": "FOUNDER_PAPER_ACCEPT",
                    "NO_PROMOTE": True,
                    "paper_enable": True,
                    "news_veto_enabled": _nve(),
                },
            )
        try:
            from backtest_engine.okala_in_paper import detect_okala_paper_signals
        except Exception as exc:  # pragma: no cover
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="DATA_INSUFFICIENT",
                data_gaps=list(ticket.data_gaps)
                + [f"DATA_INSUFFICIENT: okala_in_paper import failed ({exc.__class__.__name__})"],
                vetoes=vetoes,
                provenance_extra=base_prov,
            )
        und = str(ticket.underlying or "").upper()
        hits = detect_okala_paper_signals(
            und,
            bars,
            session_kind=str(ticket.session_kind or "") if _nve() else "NORMAL",
            veto_reasons=(
                list(ticket.top_veto_reasons) + list(ticket.vetoes) if _nve() else []
            ),
        )
        hit = next((h for h in hits if h.mix_id == candidate_id), None)
        if hit is None:
            return EvaluatorResult(
                available=True,
                raw_lean="HOLD",
                final_lean="HOLD",
                outcome="WATCH",
                data_gaps=list(ticket.data_gaps),
                vetoes=vetoes,
                provenance_extra={
                    **base_prov,
                    "founder_label": "FOUNDER_PAPER_ACCEPT",
                    "NO_PROMOTE": True,
                    "okala_hits": len(hits),
                    "news_veto_enabled": _nve(),
                },
            )
        lean_side = "BUY_CE" if hit.lean == "CE" else "BUY_PE"
        return EvaluatorResult(
            available=True,
            raw_lean=lean_side,
            final_lean=lean_side,
            outcome=lean_side,
            data_gaps=list(ticket.data_gaps) + list(hit.data_gaps),
            vetoes=vetoes,
            provenance_extra={
                **base_prov,
                "founder_label": "FOUNDER_PAPER_ACCEPT",
                "NO_PROMOTE": True,
                "eligibility": hit.eligibility,
                "okala_cell": hit.cell,
                "okala_setup": hit.setup,
                "okala_regime": hit.regime,
                "research_wr_robust": hit.wr_robust,
                "research_n": hit.n,
                "win_rate_claim": None,
                "reasons": hit.reasons,
                "news_veto_enabled": _nve(),
            },
        )

    # Fallback: bound but unknown kind → honest DI
    return EvaluatorResult(
        available=True,
        raw_lean="HOLD",
        final_lean="HOLD",
        outcome="DATA_INSUFFICIENT",
        data_gaps=list(dict.fromkeys(list(ticket.data_gaps) + [bind.reason])),
        vetoes=vetoes,
        provenance_extra=base_prov,
    )


def _from_ticket(
    ticket: PaperTicket,
    vetoes: list[str],
    base_prov: dict[str, Any],
    *,
    inherit: bool,
) -> EvaluatorResult:
    _ = inherit
    raw = ticket.lean
    final = raw
    gaps = list(ticket.data_gaps)
    if ticket.risk_veto:
        outcome = "VETOED"
        final = "HOLD"
    elif gaps:
        outcome = "STALE"
    else:
        outcome = final
    return EvaluatorResult(
        available=True,
        raw_lean=raw,
        final_lean=final,
        outcome=outcome,
        data_gaps=gaps,
        vetoes=vetoes,
        provenance_extra=base_prov,
    )
