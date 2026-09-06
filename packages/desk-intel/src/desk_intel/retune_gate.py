"""Retune gate stubs for POST_MARKET recon.

Nightly never writes production params. It tags the session and emits
RETUNE_PROPOSAL with status BACKTEST_REQUIRED. Default: keep current strategy.
Do not invent backtest results. Do not live-trade.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from desk_intel.schema import (
    LifecycleRecord,
    MarketSignal,
    NewsEvent,
    RetuneProposal,
    SessionKind,
    SessionTag,
)

RETUNE_KIND = "RETUNE_PROPOSAL"
NIGHTLY_RETUNE_STATUS = "BACKTEST_REQUIRED"

# Paths nightly must never overwrite (relative to repo root).
FORBIDDEN_PRODUCTION_PARAM_PATHS = (
    "config/workspace.yaml",
    "teams/04_quant/docs/candidates/",
    "packages/indicators/",
)

# Calendar / print tags — not the generic yaml source stamp MACRO_EVENT.
_CALENDAR_TAGS = frozenset(
    {"RBI", "FOMC", "CPI", "NFP", "GDP", "MOSPI", "CRUDE", "EIA", "MPC"}
)
_MACRO_KEYWORDS = frozenset(
    {
        "gdp",
        "pmi",
        "cpi",
        "wpi",
        "iip",
        "rbi",
        "mpc",
        "repo",
        "fomc",
        "fed",
        "nfp",
        "payroll",
        "budget",
        "mospi",
        "crude",
        "oil",
        "brent",
        "wti",
    }
)
_CALENDAR_EVENTS = frozenset(
    {"RBI_WATCH", "CPI_PRINT", "FOMC", "GDP_PRINT", "NFP_PRINT", "CRUDE_MOVE"}
)

_METRICS_REQUIRED = ("expectancy", "profit_factor", "max_drawdown")


def event_is_news_or_calendar(event: NewsEvent) -> bool:
    """True when the headline is a print/calendar row, not a generic RSS stamp."""
    tags = {str(t) for t in (event.tags or [])}
    if tags & _CALENDAR_TAGS:
        return True
    hits = {str(k).lower() for k in (event.keywords_hit or [])}
    if hits & _MACRO_KEYWORDS:
        return True
    if str(event.event or "") in _CALENDAR_EVENTS:
        return True
    source = str(event.source_id or "").lower()
    if "calendar" in source:
        return True
    return False


def _news_day_reasons(
    signals: Iterable[MarketSignal],
    events: Optional[Iterable[NewsEvent]],
) -> list[str]:
    reasons: list[str] = []
    for event in events or []:
        if event_is_news_or_calendar(event):
            reasons.append(
                f"news+calendar: {event.event or event.source_id} ({event.headline[:80]})"
            )
    for sig in signals:
        if "MACRO_EVENT" in (sig.tags or []):
            reasons.append(f"signal:{sig.id}:MACRO_EVENT")
        for veto in sig.vetoes or []:
            if "event_window" in veto:
                reasons.append(f"signal:{sig.id}:event_window")
                break
    return reasons


def _expiry_reasons(
    day: str,
    signals: Iterable[MarketSignal],
    records: Optional[Iterable[LifecycleRecord]] = None,
) -> list[str]:
    _ = records
    reasons: list[str] = []
    for sig in signals:
        expiry = (sig.expiry or "").strip()
        if expiry and expiry == day:
            reasons.append(f"signal:{sig.id}:expiry={expiry}")
        for veto in sig.vetoes or []:
            if "expiry_day" in veto:
                reasons.append(f"signal:{sig.id}:expiry_day")
                break
    return reasons


def classify_session(
    *,
    day: str,
    signals: Optional[list[MarketSignal]] = None,
    events: Optional[list[NewsEvent]] = None,
    records: Optional[list[LifecycleRecord]] = None,
) -> SessionTag:
    """Tag NEWS_DAY / EXPIRY / NORMAL. Both flags may be set; then not NORMAL."""
    sigs = signals or []
    news_reasons = _news_day_reasons(sigs, events)
    expiry_reasons = _expiry_reasons(day, sigs, records)
    flags: list[str] = []
    if news_reasons:
        flags.append("NEWS_DAY")
    if expiry_reasons:
        flags.append("EXPIRY")
    if "NEWS_DAY" in flags:
        kind: SessionKind = "NEWS_DAY"
    elif "EXPIRY" in flags:
        kind = "EXPIRY"
    else:
        kind = "NORMAL"
        flags = ["NORMAL"]
    return SessionTag(
        kind=kind,
        flags=flags,
        reasons=news_reasons + expiry_reasons,
        usable_for_retune_sample=kind == "NORMAL",
    )


def build_retune_proposal(
    *,
    session: SessionTag,
    candidate_notes: Optional[list[str]] = None,
) -> RetuneProposal:
    """Always BACKTEST_REQUIRED. Never fills backtest_results. Never production write."""
    return RetuneProposal(
        kind=RETUNE_KIND,
        status=NIGHTLY_RETUNE_STATUS,
        keep_current_strategy=True,
        production_params_written=False,
        handoff="REVIEW",
        backtest_owner="06_backtesting",
        session_kind=session.kind,
        session_flags=list(session.flags),
        session_usable_for_retune_sample=session.usable_for_retune_sample,
        oos_non_event_required=True,
        metrics_required=list(_METRICS_REQUIRED),
        one_day_pnl_is_not_evidence=True,
        backtest_results=None,
        candidate_notes=list(candidate_notes or []),
        note=(
            "Default: keep current strategy. PhD REVIEW only. "
            "06 must backtest OOS + NORMAL days before any promote. "
            "Do not invent metrics."
        ),
    )


def assert_no_production_param_write(written_paths: Iterable[Optional[str]]) -> None:
    """Nightly may persist recon JSON, PhD markdown, and paper ledger only."""
    for raw in written_paths:
        if not raw:
            continue
        text = str(raw).replace("\\", "/")
        for forbidden in FORBIDDEN_PRODUCTION_PARAM_PATHS:
            if forbidden.rstrip("/") in text:
                raise RuntimeError(
                    f"retune gate: refused production param write: {raw}"
                )


def proposal_dict(proposal: RetuneProposal) -> dict[str, Any]:
    return proposal.to_dict()
