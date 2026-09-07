"""Agent role implementations (TradingAgents-inspired, India paper rules)."""

from __future__ import annotations

import json
from typing import Optional

from trading_agents_india.fixtures import MarketContext
from trading_agents_india.hooks.event_memory import (
    analog_memory_note,
    classify_session_kind,
    news_hold_reasons,
    news_veto_enabled,
    score_premarket_sentiment,
)
from trading_agents_india.llm import LlmClient
from trading_agents_india.personas import resolve_by_pipeline_role
from trading_agents_india.schemas import AgentReport, Lean, SessionKind

_CONF_LABELS = {
    "very low": 0.15,
    "low": 0.25,
    "medium": 0.5,
    "med": 0.5,
    "moderate": 0.5,
    "high": 0.75,
    "very high": 0.9,
}

# Default LLM budget: boss + risk + news only (cut ~25 calls/tick fan-out).
# Others stay rules-only unless Settings/env expands the set.
LLM_LEAN_ROLES = frozenset({"news_analyst", "boss_research_manager", "risk_committee"})


def _parse_confidence(raw: object, default: float) -> float:
    """Accept 0-1 floats, percents, or Low/Medium/High labels from the LLM."""
    if raw is None or raw is False or raw == "":
        return default
    if isinstance(raw, (int, float)):
        val = float(raw)
        if val > 1.0 and val <= 100.0:
            val = val / 100.0
        return max(0.0, min(1.0, val))
    text = str(raw).strip().lower().replace("%", "")
    if text in _CONF_LABELS:
        return _CONF_LABELS[text]
    try:
        val = float(text)
    except ValueError:
        return default
    if val > 1.0 and val <= 100.0:
        val = val / 100.0
    return max(0.0, min(1.0, val))


def _stamp_persona(report: AgentReport) -> AgentReport:
    persona = resolve_by_pipeline_role(report.role)
    if persona:
        report.trading_agents_name = persona.trading_agents_name
        report.india_role = persona.india_role
    return report


def _llm_report(
    llm: Optional[LlmClient],
    *,
    role: str,
    system: str,
    user: str,
    fallback: AgentReport,
    allow_llm: bool = True,
) -> AgentReport:
    _stamp_persona(fallback)
    if llm is None or not allow_llm or role not in LLM_LEAN_ROLES:
        return fallback
    if getattr(llm, "skip_all", False):
        fallback.data_gaps = list(fallback.data_gaps) + [
            "DATA_INSUFFICIENT: LLM skipped this tick (big-news veto / calendar / budget)"
        ]
        return fallback
    parsed, gaps = llm.complete_json(system=system, user=user)
    if not parsed:
        fallback.data_gaps = list(fallback.data_gaps) + gaps
        return fallback
    lean = str(parsed.get("lean_hint", fallback.lean_hint)).upper()
    if lean not in ("BUY_CE", "BUY_PE", "HOLD"):
        lean = fallback.lean_hint
    return _stamp_persona(
        AgentReport(
            role=role,
            summary=str(parsed.get("summary") or fallback.summary),
            lean_hint=lean,  # type: ignore[arg-type]
            confidence=_parse_confidence(parsed.get("confidence"), fallback.confidence),
            layer="HYPOTHESIS",
            citations=list(parsed.get("citations") or fallback.citations),
            data_gaps=list(parsed.get("data_gaps") or []) + gaps,
            used_llm=True,
        )
    )


def run_news_analyst(ctx: MarketContext, llm: Optional[LlmClient] = None) -> AgentReport:
    session_kind = classify_session_kind(ctx.news, ctx.session_kind_hint)
    hold = news_hold_reasons(ctx, session_kind)
    sentiment = score_premarket_sentiment(ctx.news)
    headlines = "; ".join(n.headline for n in ctx.news) or "no headlines"
    if session_kind == "NEWS_DAY" and news_veto_enabled():
        hold_line = "Ticket HOLD — BIG_NEWS (NEWS_VETO_ENABLED)."
    elif session_kind == "NEWS_DAY":
        hold_line = (
            "NEWS_DAY noted but NEWS_VETO_ENABLED=false — does not HOLD paper ticket."
        )
    else:
        hold_line = (
            f"No mid-session news veto; premarket_sentiment={sentiment.get('label')} "
            "(soft context)."
        )
    fallback = AgentReport(
        role="news_analyst",
        summary=(
            f"News pass for {ctx.underlying}: {headlines}. "
            f"session_kind={session_kind}. {hold_line} "
            "News is notes/analog — not alpha. KEEP_ALL."
        ),
        lean_hint="HOLD",
        confidence=0.35,
        citations=[n.source_url for n in ctx.news],
        data_gaps=list(ctx.data_gaps),
    )
    if session_kind == "NEWS_DAY" and news_veto_enabled():
        fallback.lean_hint = "HOLD"
        fallback.citations = fallback.citations + hold[:2]
    return _llm_report(
        llm,
        role="news_analyst",
        system=(
            "You are the India desk news analyst for NIFTY/BANKNIFTY/SENSEX index options. "
            "Hold the customer ticket ONLY when NEWS_VETO_ENABLED and BIG_NEWS. "
            "When NEWS_VETO_ENABLED=false, note headlines but do not force HOLD. "
            "Routine/fixture MACRO noise is pre-market sentiment context — not a mid-session veto. "
            "Never fake alpha, never delete strategies. "
            "Return JSON: summary, lean_hint (BUY_CE|BUY_PE|HOLD), confidence 0-1, citations[], data_gaps[]."
        ),
        user=json.dumps(
            {
                **ctx.to_prompt_blob(),
                "premarket_sentiment": sentiment,
                "news_veto_enabled": news_veto_enabled(),
            }
        ),
        fallback=fallback,
    )


def run_sentiment_analyst(ctx: MarketContext, llm: Optional[LlmClient] = None) -> AgentReport:
    fallback = AgentReport(
        role="sentiment_analyst",
        summary=(
            f"Sentiment for {ctx.underlying}: {ctx.sentiment_label}. "
            "India index social/news sentiment feed not validated — no StockTwits import."
        ),
        lean_hint="HOLD",
        confidence=0.1,
        data_gaps=[
            "DATA_INSUFFICIENT: India social sentiment feed not wired",
            "REJECT: StockTwits/Reddit as SOURCE_FACT for NSE index options",
        ],
    )
    return _llm_report(
        llm,
        role="sentiment_analyst",
        system=(
            "You are sentiment analyst for Indian index options. If data is insufficient, say so. "
            "Do not invent Reddit/StockTwits reads. "
            "JSON: summary, lean_hint (BUY_CE|BUY_PE|HOLD), confidence (number 0-1 only), citations[], data_gaps[]."
        ),
        user=json.dumps(ctx.to_prompt_blob()),
        fallback=fallback,
    )


def run_technical_analyst(ctx: MarketContext, llm: Optional[LlmClient] = None) -> AgentReport:
    lean: Lean = "HOLD"
    if ctx.chain_lean == "CE":
        lean = "BUY_CE"
    elif ctx.chain_lean == "PE":
        lean = "BUY_PE"
    prem = ctx.premium_lean or {}
    prem_note = ""
    if prem:
        prem_note = (
            f" Premium lean source={prem.get('source')} lean={prem.get('lean')} "
            f"layer={prem.get('layer')}."
        )
    fallback = AgentReport(
        role="technical_analyst",
        summary=(
            f"Chain lean fixture={ctx.chain_lean}; trend={ctx.trend_plain}. "
            f"{ctx.technical_note} Indicators confirm-or-kill only.{prem_note}"
        ),
        lean_hint=lean,
        confidence=0.4 if lean != "HOLD" else 0.25,
        citations=["teams/04_quant/docs/SIGNAL_STAGING.md"],
        data_gaps=list(ctx.data_gaps) + list(prem.get("data_gaps") or []),
    )
    return _llm_report(
        llm,
        role="technical_analyst",
        system=(
            "Technical analyst for NSE index options. 5m ST/MACD/RSI are confirm-or-kill, not entry. "
            "Map chain lean CE→BUY_CE, PE→BUY_PE, else HOLD. "
            "If premium_lean.source=index_proxy, label HYPOTHESIS. JSON fields as usual."
        ),
        user=json.dumps(ctx.to_prompt_blob()),
        fallback=fallback,
    )


def run_chain_watcher(ctx: MarketContext, llm: Optional[LlmClient] = None) -> AgentReport:
    """Option chain watcher — fake-breakout / thin-wall hypotheses; DI if no data."""
    watch = ctx.chain_watch or {}
    flag = str(watch.get("hypothesis_flag") or "NONE")
    source = str(watch.get("source") or "fixture")
    lean: Lean = "HOLD"
    if ctx.chain_lean == "CE":
        lean = "BUY_CE"
    elif ctx.chain_lean == "PE":
        lean = "BUY_PE"
    # Thin wall / fake breakout → do not force directional; prefer HOLD overlay
    if flag in ("THIN_WALL_HYPOTHESIS", "FAKE_BREAKOUT_HYPOTHESIS", "BOTH_HYPOTHESIS"):
        if lean != "HOLD":
            # Soften: keep lean_hint from chain but note hypothesis risk in summary
            pass
    walls = watch.get("wall_notes") or []
    summary = str(watch.get("summary") or (
        f"Chain watcher {ctx.underlying}: source={source} flag={flag}. "
        "Fake-breakout/thin-wall are HYPOTHESIS only."
    ))
    if walls:
        summary = summary + " " + "; ".join(str(w) for w in walls[:3])
    gaps = list(ctx.data_gaps) + list(watch.get("data_gaps") or [])
    if source in ("fixture", "unavailable"):
        gaps.append("DATA_INSUFFICIENT: live chain walls not validated")
    fallback = AgentReport(
        role="chain_watcher",
        summary=summary,
        lean_hint=lean if flag == "NONE" else "HOLD",
        confidence=0.35 if source == "dhan_live" else 0.2,
        layer="HYPOTHESIS",
        citations=[
            "teams/05_analysis/docs/DESK_INTELLIGENCE.md",
            "packages/trading_agents_india/hooks/chain.py",
        ],
        data_gaps=gaps,
    )
    return _llm_report(
        llm,
        role="chain_watcher",
        system=(
            "You are the India option-chain watcher. Flag fake-breakout and thin-wall "
            "as HYPOTHESIS only. If data insufficient, say DATA_INSUFFICIENT. "
            "Never invent OI walls. Prefer HOLD when walls are thin or breakout suspect. "
            "JSON: summary, lean_hint (BUY_CE|BUY_PE|HOLD), confidence, citations, data_gaps."
        ),
        user=json.dumps(ctx.to_prompt_blob()),
        fallback=fallback,
    )


def run_bull(ctx: MarketContext, prior: list[AgentReport], llm: Optional[LlmClient] = None) -> AgentReport:
    tech = next((r for r in prior if r.role == "technical_analyst"), None)
    hint: Lean = tech.lean_hint if tech and tech.lean_hint == "BUY_CE" else "BUY_CE"
    fallback = AgentReport(
        role="bull_researcher",
        summary=(
            f"Bull case {ctx.underlying}: argue CE only if chain/trend support; "
            f"still subordinate to news hold. Prior tech={tech.lean_hint if tech else 'n/a'}."
        ),
        lean_hint=hint if ctx.chain_lean == "CE" else "HOLD",
        confidence=0.45 if ctx.chain_lean == "CE" else 0.2,
        citations=["TradingAgents bull role adapted"],
    )
    return _llm_report(
        llm,
        role="bull_researcher",
        system=(
            "Bull researcher for India index CE buys. Challenge weak CE cases. "
            "Never override NEWS_DAY hold. JSON: summary, lean_hint, confidence, citations, data_gaps."
        ),
        user=json.dumps({"ctx": ctx.to_prompt_blob(), "prior": [r.to_dict() for r in prior]}),
        fallback=fallback,
    )


def run_bear(ctx: MarketContext, prior: list[AgentReport], llm: Optional[LlmClient] = None) -> AgentReport:
    tech = next((r for r in prior if r.role == "technical_analyst"), None)
    fallback = AgentReport(
        role="bear_researcher",
        summary=(
            f"Bear case {ctx.underlying}: argue PE or HOLD; emphasize event risk and false CE sprays. "
            f"Prior tech={tech.lean_hint if tech else 'n/a'}."
        ),
        lean_hint="BUY_PE" if ctx.chain_lean == "PE" else "HOLD",
        confidence=0.45 if ctx.chain_lean == "PE" else 0.35,
        citations=["TradingAgents bear role adapted"],
    )
    return _llm_report(
        llm,
        role="bear_researcher",
        system=(
            "Bear researcher for India index options. Prefer HOLD/PE when mixed or news risk. "
            "JSON: summary, lean_hint, confidence, citations, data_gaps."
        ),
        user=json.dumps({"ctx": ctx.to_prompt_blob(), "prior": [r.to_dict() for r in prior]}),
        fallback=fallback,
    )


def run_boss(
    ctx: MarketContext,
    prior: list[AgentReport],
    session_kind: SessionKind,
    default_mix: str,
    llm: Optional[LlmClient] = None,
) -> AgentReport:
    hard_news = news_veto_enabled() and session_kind in ("NEWS_DAY", "EXPIRY")
    if hard_news:
        lean: Lean = "HOLD"
    else:
        bull = next((r for r in prior if r.role == "bull_researcher"), None)
        bear = next((r for r in prior if r.role == "bear_researcher"), None)
        tech = next((r for r in prior if r.role == "technical_analyst"), None)
        chain = next((r for r in prior if r.role == "chain_watcher"), None)
        if tech and tech.lean_hint in ("BUY_CE", "BUY_PE") and tech.lean_hint == (
            bull.lean_hint if bull else tech.lean_hint
        ):
            lean = tech.lean_hint
        elif tech and bear and tech.lean_hint == bear.lean_hint and tech.lean_hint != "HOLD":
            lean = tech.lean_hint
        elif chain and chain.lean_hint in ("BUY_CE", "BUY_PE"):
            lean = chain.lean_hint
        elif ctx.chain_lean == "CE":
            lean = "BUY_CE"
        elif ctx.chain_lean == "PE":
            lean = "BUY_PE"
        else:
            lean = "HOLD"
    fallback = AgentReport(
        role="boss_research_manager",
        summary=(
            f"Boss desk call for {ctx.underlying}: lean={lean}, session={session_kind}, "
            f"news_veto_enabled={news_veto_enabled()}, "
            f"default book cited={default_mix} (KEEP_ALL; not a promote). "
            f"{analog_memory_note()}"
        ),
        lean_hint=lean,
        confidence=0.5 if lean != "HOLD" else 0.3,
        citations=[
            "teams/00_orchestrator/docs/BOSS_AGENT.md",
            "teams/04_quant/docs/MIX_CATALOG.md",
            "teams/00_orchestrator/docs/HOW_SIGNALS_WORK.md",
        ],
        data_gaps=["DATA_INSUFFICIENT: EVENT_MEMORY analogs empty"],
    )
    return _llm_report(
        llm,
        role="boss_research_manager",
        system=(
            "You are the 00 boss desk. Mandate=customer profitability over SDLC, not a claimed win rate. "
            "KEEP_ALL STRAT-001–014. When NEWS_VETO_ENABLED, BIG_NEWS/NEWS_DAY→HOLD; when false, prefer "
            "strategy/chain CE|PE over news soup. Cite MIX-DEFAULT-BUY as default book only. "
            "JSON: summary, lean_hint, confidence, citations, data_gaps."
        ),
        user=json.dumps(
            {
                "ctx": ctx.to_prompt_blob(),
                "session_kind": session_kind,
                "news_veto_enabled": news_veto_enabled(),
                "default_mix": default_mix,
                "prior": [r.to_dict() for r in prior],
            }
        ),
        fallback=fallback,
    )


def run_trader(boss: AgentReport, session_kind: SessionKind) -> AgentReport:
    """Paper CE/PE/HOLD only — never places live orders."""
    if news_veto_enabled() and session_kind != "NORMAL":
        lean = "HOLD"
    else:
        lean = boss.lean_hint
    if lean not in ("BUY_CE", "BUY_PE", "HOLD"):
        lean = "HOLD"
    return _stamp_persona(
        AgentReport(
            role="trader",
            summary=(
                f"Paper trader proposal: {lean}. Execution refused. "
                "Emits paper CE/PE/HOLD only. No /alerts/orders. "
                "Levels not invented when DATA_INSUFFICIENT."
            ),
            lean_hint=lean,  # type: ignore[arg-type]
            confidence=boss.confidence * 0.9,
            citations=[
                "packages/desk-intel paper_signal adapter pattern",
                "trading_agents_india.handoffs trader→risk",
            ],
            data_gaps=["DATA_INSUFFICIENT: option premium fill model not claimed"],
        )
    )


def run_risk(
    ctx: MarketContext,
    trader: AgentReport,
    session_kind: SessionKind,
    llm: Optional[LlmClient] = None,
) -> AgentReport:
    vetoes = news_hold_reasons(ctx, session_kind)
    hard = news_veto_enabled() and session_kind != "NORMAL"
    if hard:
        lean: Lean = "HOLD"
        summary = (
            f"Risk triad (agg/cons/neutral collapsed for v0): VETO lean→HOLD. "
            + "; ".join(vetoes[:3])
        )
        conf = 0.7
    else:
        lean = trader.lean_hint
        summary = (
            "Risk triad: news veto parked or NORMAL session. "
            "Conservative hat still caps confidence; aggressive hat may not force size. "
            f"news_veto_enabled={news_veto_enabled()}."
        )
        conf = 0.45
        if trader.lean_hint == "HOLD":
            vetoes.append("neutral_risk: no directional edge after debate")
    fallback = AgentReport(
        role="risk_committee",
        summary=summary,
        lean_hint=lean,
        confidence=conf,
        citations=[
            "teams/06_backtesting/docs/EVENT_MEMORY.md",
            "teams/05_analysis/docs/SIGNAL_FUSION.md",
            "teams/00_orchestrator/docs/HOW_SIGNALS_WORK.md",
        ],
        data_gaps=list(ctx.data_gaps),
    )
    # Attach veto strings into citations for downstream
    fallback.citations = fallback.citations + vetoes
    return _llm_report(
        llm,
        role="risk_committee",
        system=(
            "Risk committee for India index options paper desk. "
            "On BIG_NEWS NEWS_DAY/EXPIRY you MUST lean HOLD only when NEWS_VETO_ENABLED. "
            "When NEWS_VETO_ENABLED=false, do not veto solely for news. Never approve live orders. "
            "JSON: summary, lean_hint, confidence, citations (include veto strings), data_gaps."
        ),
        user=json.dumps(
            {
                "ctx": ctx.to_prompt_blob(),
                "trader": trader.to_dict(),
                "session_kind": session_kind,
                "news_veto_enabled": news_veto_enabled(),
            }
        ),
        fallback=fallback,
    )
