"""Fuse news_bias + chain_bias → MARKET_SIGNAL.

Confirm means checklist + data, not operator omniscience.
Do not depend only on canned strategies. Output is bias / risk regime.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from config.load import DeskIntelSettings
from desk_intel.news_ingest import aggregate_news_bias
from desk_intel.schema import (
    COMPLIANCE_NOTE,
    DEFAULT_SENTIMENT_WINDOWS,
    ChainBias,
    MarketSignal,
    NewsEvent,
    RiskBias,
    SentimentWindow,
    SignalLean,
)
from desk_intel.outcomes import initial_stage, still_valid
from desk_intel.time_ist import in_opening_drive, now_ist, parse_rss_datetime

# ROOM TO EDIT: confirmation weights. Never auto-fire orders from these.
_CONF_CAP = 0.72  # not omniscient


def _event_in_veto_window(
    events: list[NewsEvent],
    minutes: int,
    now: Optional[datetime] = None,
) -> list[NewsEvent]:
    current = now or now_ist()
    hot: list[NewsEvent] = []
    for event in events:
        if "MACRO_EVENT" not in (event.tags or []):
            continue
        when = parse_rss_datetime(event.time_ist)
        if when is None:
            continue
        delta_min = abs((current - when).total_seconds()) / 60.0
        if delta_min <= minutes:
            hot.append(event)
    return hot


def _checklist_vetoes(
    events: list[NewsEvent],
    chain: ChainBias,
    news_bias: RiskBias,
    settings: DeskIntelSettings,
) -> list[str]:
    """Persona CONFIRM/VETO list. See teams/00_orchestrator/docs/PERSONA_DESK.md."""
    vetoes: list[str] = []
    hot = _event_in_veto_window(events, settings.event_veto_minutes)
    if hot:
        vetoes.append(
            f"event_window: {len(hot)} MACRO_EVENT headline(s) within "
            f"{settings.event_veto_minutes}m — do not let a canned indicator override the print"
        )
    if news_bias == "NO_TRADE":
        vetoes.append("news_regime NO_TRADE (halt / unknown print keywords)")
    if news_bias == "RISK_OFF" and chain.lean == "CE":
        vetoes.append("tape_vs_headline: RISK_OFF news vs CE buildup — no CE spray")
    if news_bias == "RISK_ON" and chain.lean == "PE":
        vetoes.append("tape_vs_headline: RISK_ON news vs PE buildup — no PE spray")
    if in_opening_drive(settings.opening_drive_until):
        vetoes.append(
            f"opening_drive: before {settings.opening_drive_until} IST — wait for drive/failure, don't fade the first spike"
        )
    expiry = (chain.expiry or "").strip()
    today = now_ist().date().isoformat()
    if expiry == today:
        vetoes.append("expiry_day: gamma/pin risk — technical trend-follow is on probation")
    crudeish = [
        e
        for e in events
        if any(k in (e.keywords_hit or []) for k in ("crude", "oil", "brent", "wti"))
        or "CRUDE" in (e.tags or [])
    ]
    if crudeish:
        vetoes.append(
            "crude_overlay: energy/INR/risk-off is a HYPOTHESIS — not automatic BUY PE"
        )
    # Fake breakdown stub: spot through PE wall but PE OI not covering.
    if (
        chain.spot is not None
        and chain.pe_oi_wall is not None
        and chain.spot < chain.pe_oi_wall
        and chain.atm_pe_buildup < 0
        and chain.atm_ce_buildup > 0
    ):
        vetoes.append(
            "fake_breakdown_risk: spot below PE wall while ATM PE OI falls / CE OI rises — PE spray is the trap until reclaim fails"
        )
    return vetoes


def _lean_from_agreement(
    news_bias: RiskBias,
    chain_lean: str,
    vetoes: list[str],
) -> SignalLean:
    blocking = [v for v in vetoes if v.startswith(("event_window", "news_regime", "opening_drive"))]
    if news_bias == "NO_TRADE" or chain_lean == "NO_TRADE":
        return "NO_TRADE"
    if blocking:
        return "NO_TRADE"
    if any(v.startswith("crude_overlay") for v in vetoes) and news_bias == "RISK_OFF":
        # Crude 90→95-style: regime can be RISK_OFF; PE is not automatic.
        return "NEUTRAL"
    if "tape_vs_headline" in " ".join(vetoes):
        return "NEUTRAL"
    if news_bias == "RISK_ON" and chain_lean == "CE":
        return "BUY_CE"
    if news_bias == "RISK_OFF" and chain_lean == "PE":
        return "BUY_PE"
    if news_bias == "MIXED":
        if chain_lean == "CE":
            return "NEUTRAL"
        if chain_lean == "PE":
            return "NEUTRAL"
    # Chain-only (news MIXED/empty): still not a canned strategy — downrank in confidence.
    if chain_lean == "CE":
        return "BUY_CE"
    if chain_lean == "PE":
        return "BUY_PE"
    return "NEUTRAL"


def _confidence(
    lean: SignalLean,
    news_bias: RiskBias,
    chain: ChainBias,
    vetoes: list[str],
    events: list[NewsEvent],
) -> float:
    if lean == "NO_TRADE":
        return 0.15
    score = 0.34
    agreed = (
        (news_bias == "RISK_ON" and chain.lean == "CE")
        or (news_bias == "RISK_OFF" and chain.lean == "PE")
    )
    if agreed:
        score += 0.18
    if abs(chain.wing_ce_buildup - chain.wing_pe_buildup) > 20_000:
        score += 0.08
    if events:
        score += 0.04
    score -= 0.08 * min(len(vetoes), 4)
    if news_bias == "MIXED":
        score -= 0.06
    return max(0.12, min(_CONF_CAP, round(score, 2)))


def mock_sentiment_windows(
    settings: DeskIntelSettings,
    *,
    lean: SignalLean,
    confidence: float,
    news_bias: RiskBias,
    chain_lean: str,
) -> list[SentimentWindow]:
    """Named 10m/15m/30m/1h slots for later dashboard bind. Mock, not measured."""
    windows = list(settings.sentiment_windows or DEFAULT_SENTIMENT_WINDOWS)
    if not windows:
        windows = list(DEFAULT_SENTIMENT_WINDOWS)
    out: list[SentimentWindow] = []
    for horizon in windows:
        out.append(
            SentimentWindow(
                horizon=str(horizon),
                lean=lean,
                confidence=confidence,
                news_bias=news_bias,
                chain_lean=chain_lean,  # type: ignore[arg-type]
                mock=True,
                note=(
                    f"Mock fusion bind for {horizon} — not a rolling measured window. "
                    "Dashboard may attach later; do not treat as edge."
                ),
            )
        )
    return out


def fuse_one(
    chain: ChainBias,
    events: list[NewsEvent],
    settings: DeskIntelSettings,
) -> MarketSignal:
    news_bias = aggregate_news_bias(events)
    vetoes = _checklist_vetoes(events, chain, news_bias, settings)
    lean = _lean_from_agreement(news_bias, chain.lean, vetoes)
    reasons = [
        f"news_bias={news_bias} (keyword HYPOTHESIS, surprise mostly UNKNOWN)",
        f"chain_lean={chain.lean} from OI/PCR/buildup stub",
        *chain.reasons[:8],
    ]
    if any("crude" in (e.event or "").lower() or "CRUDE" in e.tags for e in events):
        reasons.append(
            "Crude 90→95-style move: possible energy/INR/risk-off HYPOTHESIS, not automatic PE spray"
        )
    tags = ["DESK_INTEL", "HYPOTHESIS"]
    if any("MACRO_EVENT" in e.tags for e in events):
        tags.append("MACRO_EVENT")
    conf = _confidence(lean, news_bias, chain, vetoes, events)
    signal = MarketSignal(
        id=f"desk-{chain.underlying.lower()}-{uuid4().hex[:8]}",
        underlying=chain.underlying,
        lean=lean,
        confidence=conf,
        risk_regime=news_bias if lean != "NO_TRADE" else "NO_TRADE",
        reasons=reasons,
        vetoes=vetoes,
        timestamp=chain.as_of_ist,
        news_bias=news_bias,
        chain_bias=chain.lean,
        tags=tags,
        expiry=chain.expiry,
        atm_strike=chain.atm_strike,
        dry_run=chain.dry_run,
        layer="HYPOTHESIS",
        compliance=COMPLIANCE_NOTE,
        sentiment_windows=mock_sentiment_windows(
            settings,
            lean=lean,
            confidence=conf,
            news_bias=news_bias,
            chain_lean=chain.lean,
        ),
    )
    signal.stage = initial_stage(signal)
    signal.outcome = None
    signal.still_valid = still_valid(signal.stage, signal.outcome)
    return signal


def fuse(
    chain_biases: list[ChainBias],
    events: list[NewsEvent],
    settings: DeskIntelSettings,
) -> list[MarketSignal]:
    return [fuse_one(chain, events, settings) for chain in chain_biases]
