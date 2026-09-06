"""Orchestration pipeline: analysts → debate → boss → trader → risk → paper ticket."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence
from zoneinfo import ZoneInfo

from trading_agents_india import COMPLIANCE_NOTE
from trading_agents_india.agents import (
    run_bear,
    run_boss,
    run_bull,
    run_news_analyst,
    run_risk,
    run_sentiment_analyst,
    run_technical_analyst,
    run_trader,
)
from trading_agents_india.config import Settings, load_settings
from trading_agents_india.fixtures import MarketContext, fixture_contexts
from trading_agents_india.hooks.desk import try_load_desk_context
from trading_agents_india.hooks.event_memory import classify_session_kind
from trading_agents_india.hooks.news import gather_news
from trading_agents_india.kb import AgentKB
from trading_agents_india.llm import LlmClient
from trading_agents_india.mode import (
    Mode,
    attempt_live_order,
    evaluate_live_gate,
    normalize_mode,
)
from trading_agents_india.personas import registry_payload
from trading_agents_india.schemas import PaperTicket, SessionResult, Stage


def lean_ok(value: str) -> bool:
    return value in ("BUY_CE", "BUY_PE", "HOLD")


def _now_ist() -> str:
    try:
        return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
    except Exception:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _resolve_context(
    underlying: str,
    *,
    prefer_desk: bool,
    gather_india_news: bool,
) -> tuple[MarketContext, list[str]]:
    gaps: list[str] = []
    fixtures = fixture_contexts()
    base = fixtures.get(underlying.upper())
    if base is None:
        raise ValueError(f"unsupported underlying: {underlying}")
    ctx = base
    if prefer_desk:
        desk_ctx, desk_gaps = try_load_desk_context(underlying)
        gaps.extend(desk_gaps)
        if desk_ctx is not None:
            ctx = desk_ctx
    if gather_india_news:
        bundle = gather_news(prefer_live_rss=False)
        gaps.extend(bundle.data_gaps)
        if bundle.items:
            # Overlay India news; keep fixture lean/trend (do not invent chain).
            ctx = MarketContext(
                underlying=ctx.underlying,
                chain_lean=ctx.chain_lean,
                trend_plain=ctx.trend_plain,
                news=list(bundle.items),
                session_kind_hint=ctx.session_kind_hint,
                sentiment_label=ctx.sentiment_label,
                technical_note=ctx.technical_note,
                data_gaps=list(ctx.data_gaps) + list(bundle.data_gaps),
            )
    return ctx, gaps


def run_underlying_session(
    ctx: MarketContext,
    settings: Settings,
    llm: Optional[LlmClient],
) -> PaperTicket:
    session_kind = classify_session_kind(ctx.news, ctx.session_kind_hint)
    reports = []

    news = run_news_analyst(ctx, llm)
    sentiment = run_sentiment_analyst(ctx, llm)
    technical = run_technical_analyst(ctx, llm)
    reports.extend([news, sentiment, technical])

    bull = run_bull(ctx, reports, llm)
    bear = run_bear(ctx, reports, llm)
    reports.extend([bull, bear])

    boss = run_boss(ctx, reports, session_kind, settings.default_mix, llm)
    reports.append(boss)

    trader = run_trader(boss, session_kind)
    reports.append(trader)

    risk = run_risk(ctx, trader, session_kind, llm)
    reports.append(risk)

    risk_veto = session_kind in ("NEWS_DAY", "EXPIRY")
    if not risk_veto and risk.lean_hint == "HOLD":
        # Neutral/no-edge HOLD is WATCH, not necessarily a hard news veto
        risk_veto = any(
            c.startswith(("NEWS_DAY", "EXPIRY", "cited_news")) for c in risk.citations
        )

    lean = risk.lean_hint if lean_ok(risk.lean_hint) else "HOLD"
    if risk_veto:
        lean = "HOLD"

    stage: Stage
    if risk_veto:
        stage = "VETOED"
        lean = "HOLD"
    elif lean == "HOLD":
        stage = "WATCH"
    else:
        stage = "EARLY"  # v0: never CONFIRMED from agent loop alone

    vetoes = [
        c
        for c in risk.citations
        if c.startswith(("NEWS_DAY", "EXPIRY", "cited_news", "neutral_risk"))
    ]
    reasons = [
        f"boss: {boss.summary[:180]}",
        f"tech: {technical.summary[:120]}",
        f"bull: {bull.summary[:100]}",
        f"bear: {bear.summary[:100]}",
    ]
    if vetoes:
        reasons.extend(vetoes[:4])

    gaps: list[str] = []
    for r in reports:
        gaps.extend(r.data_gaps)
    gaps.extend(ctx.data_gaps)
    # de-dupe preserve order
    seen = set()
    uniq_gaps = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            uniq_gaps.append(g)

    return PaperTicket(
        underlying=ctx.underlying,  # type: ignore[arg-type]
        lean=lean,  # type: ignore[arg-type]
        stage=stage,
        reasons=reasons,
        risk_veto=risk_veto,
        vetoes=vetoes,
        session_kind=session_kind,
        default_mix_cited=settings.default_mix,
        confidence=min(0.72, float(risk.confidence)),
        data_gaps=uniq_gaps[:12],
        bull_summary=bull.summary,
        bear_summary=bear.summary,
        news_summary=news.summary,
        sentiment_summary=sentiment.summary,
        technical_summary=technical.summary,
        risk_summary=risk.summary,
        boss_summary=boss.summary,
        reports=[r.to_dict() for r in reports],
    )


def run_session(
    *,
    underlyings: Optional[Sequence[str]] = None,
    dry_run: bool = True,
    use_llm: bool = False,
    prefer_desk: bool = False,
    gather_india_news: bool = False,
    persist: bool = True,
    mode: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> SessionResult:
    settings = settings or load_settings()
    names = tuple(underlyings) if underlyings else settings.underlyings
    llm: Optional[LlmClient] = None
    openai_used = False
    session_gaps: list[str] = []

    resolved_mode: Mode
    if mode is not None:
        resolved_mode = normalize_mode(mode)
    elif dry_run:
        resolved_mode = "PAPER"
    else:
        resolved_mode = "PAPER"

    live_gate = evaluate_live_gate(resolved_mode)
    session_gaps.extend(live_gate.reasons)
    live_attempt = None
    if resolved_mode == "LIVE":
        live_attempt = attempt_live_order(
            mode="LIVE",
            payload={"note": "trading_agents_india LIVE stub — always refuse"},
        )
        session_gaps.append(
            "VALIDATION: LIVE mode requested — orders refused (see live_order_attempt)"
        )

    if use_llm:
        llm = LlmClient(settings.openai_model, enabled=True)
        if llm.enabled:
            openai_used = True
        else:
            session_gaps.append(
                "DATA_INSUFFICIENT: --use-llm requested but OpenAI unavailable — rule fallback"
            )
            if llm.last_error:
                session_gaps.append(f"UNKNOWN: {llm.last_error}")
    elif not settings.openai_key_present:
        session_gaps.append("DATA_INSUFFICIENT: OPENAI_API_KEY not set in env/.env")

    tickets: list[PaperTicket] = []
    for name in names:
        ctx, gaps = _resolve_context(
            name,
            prefer_desk=prefer_desk,
            gather_india_news=gather_india_news,
        )
        session_gaps.extend(gaps)
        tickets.append(run_underlying_session(ctx, settings, llm if use_llm else None))

    # mode string for KB: PAPER (incl dry-run) or LIVE (still refused)
    mode_label: Mode = resolved_mode

    result = SessionResult(
        as_of_ist=_now_ist(),
        mode=mode_label,
        openai_used=openai_used,
        openai_key_present=settings.openai_key_present,
        tickets=tickets,
        compliance=COMPLIANCE_NOTE,
        kb_path=str(settings.kb_path),
        data_gaps=list(dict.fromkeys(session_gaps)),
        live_gate=live_gate.to_dict(),
        live_order_attempt=live_attempt,
        personas_cited=registry_payload(),
    )

    if persist:
        kb = AgentKB(settings.kb_path)
        kb.save_session(result.to_dict())

    return result
