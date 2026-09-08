"""Orchestration pipeline: analysts → chain → debate → boss → trader → risk → paper ticket."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Sequence
from zoneinfo import ZoneInfo

from trading_agents_india import COMPLIANCE_NOTE
from trading_agents_india.agents import (
    run_bear,
    run_boss,
    run_bull,
    run_chain_watcher,
    run_news_analyst,
    run_risk,
    run_sentiment_analyst,
    run_technical_analyst,
    run_trader,
)
from trading_agents_india.config import Settings, load_settings
from trading_agents_india.fixtures import DRY_RUN_CHAIN_GAP, MarketContext, fixture_contexts
from trading_agents_india.handoffs import build_handoff_chain, validate_handoff_chain
from trading_agents_india.hooks.chain import watch_chain
from trading_agents_india.hooks.desk import try_load_desk_context
from trading_agents_india.hooks.event_memory import (
    classify_session_kind,
    news_veto_enabled,
    score_premarket_sentiment,
    top_veto_reasons,
)
from trading_agents_india.hooks.index_bars import fetch_index_bars
from trading_agents_india.hooks.news import gather_news
from trading_agents_india.hooks.premium import resolve_premium_lean
from trading_agents_india.hooks.rag import fetch_rag_context
from trading_agents_india.kb import AgentKB
from trading_agents_india.llm import LlmClient
from trading_agents_india.mix_inputs import build_reason_inputs
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


def drop_stale_dry_run_chain_gap(
    gaps: Sequence[str], *, chain_source: str
) -> list[str]:
    """Keep EVENT_MEMORY / other DI; drop fixture-only chain gap after live parse."""
    cleaned = list(gaps)
    if chain_source == "dhan_live":
        cleaned = [g for g in cleaned if g != DRY_RUN_CHAIN_GAP]
    return list(dict.fromkeys(cleaned))


def _enrich_context(
    ctx: MarketContext,
    *,
    prefer_live_chain: bool,
    mix_inputs: dict[str, Any],
) -> MarketContext:
    watch = watch_chain(
        ctx.underlying,
        fixture_lean=ctx.chain_lean,
        prefer_live=prefer_live_chain,
    )
    premium = resolve_premium_lean(
        ctx.underlying,
        prefer_live=prefer_live_chain,
        trend_plain=ctx.trend_plain,
        chain_lean=watch.chain_lean if watch.source == "dhan_live" else ctx.chain_lean,
        chain_watch=watch.to_dict(),
    )
    index = fetch_index_bars(ctx.underlying, prefer_live=prefer_live_chain)
    gaps = (
        list(ctx.data_gaps)
        + list(watch.data_gaps)
        + list(premium.data_gaps)
        + list(index.data_gaps)
    )
    gaps = drop_stale_dry_run_chain_gap(gaps, chain_source=watch.source)
    live_lean = watch.chain_lean if watch.source == "dhan_live" else ctx.chain_lean
    prem = premium.to_dict()
    prem["spot"] = watch.spot
    prem["pcr_oi"] = watch.pcr_oi
    prem["strike_count"] = watch.strike_count
    prem["expiry"] = watch.expiry
    return MarketContext(
        underlying=ctx.underlying,
        chain_lean=live_lean,
        trend_plain=ctx.trend_plain,
        news=list(ctx.news),
        session_kind_hint=ctx.session_kind_hint,
        sentiment_label=ctx.sentiment_label,
        technical_note=ctx.technical_note,
        data_gaps=list(dict.fromkeys(gaps)),
        chain_watch=watch.to_dict(),
        premium_lean=prem,
        mix_inputs=mix_inputs,
        rag_context=list(ctx.rag_context),
        index_bars=list(index.bars),
        index_bar_meta=index.to_dict(),
    )


def _resolve_context(
    underlying: str,
    *,
    prefer_desk: bool,
    gather_india_news: bool,
    prefer_live_chain: bool,
    mix_inputs: dict[str, Any],
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
            ctx = MarketContext(
                underlying=ctx.underlying,
                chain_lean=ctx.chain_lean,
                trend_plain=ctx.trend_plain,
                news=list(bundle.items),
                session_kind_hint=ctx.session_kind_hint,
                sentiment_label=ctx.sentiment_label,
                technical_note=ctx.technical_note,
                data_gaps=list(ctx.data_gaps) + list(bundle.data_gaps),
                chain_watch=dict(ctx.chain_watch),
                premium_lean=dict(ctx.premium_lean),
                mix_inputs=dict(ctx.mix_inputs),
                rag_context=list(ctx.rag_context),
                index_bars=list(ctx.index_bars),
                index_bar_meta=dict(ctx.index_bar_meta),
            )
    ctx = _enrich_context(ctx, prefer_live_chain=prefer_live_chain, mix_inputs=mix_inputs)
    gaps.extend(ctx.data_gaps)
    return ctx, list(dict.fromkeys(gaps))


def _attach_rag(ctx: MarketContext) -> MarketContext:
    snippets, rag_gaps = fetch_rag_context(ctx.underlying)
    return MarketContext(
        underlying=ctx.underlying,
        chain_lean=ctx.chain_lean,
        trend_plain=ctx.trend_plain,
        news=list(ctx.news),
        session_kind_hint=ctx.session_kind_hint,
        sentiment_label=ctx.sentiment_label,
        technical_note=ctx.technical_note,
        data_gaps=list(dict.fromkeys(list(ctx.data_gaps) + rag_gaps)),
        chain_watch=dict(ctx.chain_watch),
        premium_lean=dict(ctx.premium_lean),
        mix_inputs=dict(ctx.mix_inputs),
        rag_context=snippets,
        index_bars=list(ctx.index_bars),
        index_bar_meta=dict(ctx.index_bar_meta),
    )


def run_underlying_session(
    ctx: MarketContext,
    settings: Settings,
    llm: Optional[LlmClient],
    *,
    gather_india_news: bool = False,
) -> PaperTicket:
    session_kind = classify_session_kind(ctx.news, ctx.session_kind_hint)
    premarket = score_premarket_sentiment(ctx.news)
    # Skip OpenAI fan-out when hard-vetoed (big news / expiry) **and** veto enabled.
    active_llm = llm
    if (
        llm is not None
        and news_veto_enabled()
        and session_kind in ("NEWS_DAY", "EXPIRY")
    ):
        llm.skip_all = True  # type: ignore[attr-defined]
        active_llm = llm
    reports = []
    if llm is not None:
        # Fresh per-underlying budget so NIFTY TickBudget does not starve BN/SENSEX.
        llm.call_count = 0  # type: ignore[attr-defined]
    # Founder: no news API mid-session — keep news/sentiment on rules only.
    news_llm = active_llm if gather_india_news else None

    news = run_news_analyst(ctx, news_llm)
    sentiment = run_sentiment_analyst(ctx, news_llm)
    technical = run_technical_analyst(ctx, active_llm)
    chain = run_chain_watcher(ctx, active_llm)
    reports.extend([news, sentiment, technical, chain])

    bull = run_bull(ctx, reports, active_llm)
    bear = run_bear(ctx, reports, active_llm)
    reports.extend([bull, bear])

    boss = run_boss(ctx, reports, session_kind, settings.default_mix, active_llm)
    reports.append(boss)

    trader = run_trader(boss, session_kind)
    reports.append(trader)

    risk = run_risk(ctx, trader, session_kind, active_llm)
    reports.append(risk)

    provenance = {
        "source": str((ctx.premium_lean or {}).get("source") or "fixture_or_desk"),
        "layer": "HYPOTHESIS",
        "observed_at_ist": _now_ist(),
        "freshness_status": "STALE" if ctx.data_gaps else "FIXTURE",
        "data_gaps": list(ctx.data_gaps),
        "index_bar_count": int((ctx.index_bar_meta or {}).get("bar_count") or 0),
        "index_bar_source": str((ctx.index_bar_meta or {}).get("source") or "unavailable"),
    }
    for report in reports:
        report.provenance = dict(provenance)
    handoffs = build_handoff_chain(reports)
    handoff_errors = validate_handoff_chain(handoffs)

    risk_veto = False
    if news_veto_enabled():
        risk_veto = session_kind in ("NEWS_DAY", "EXPIRY")
        if not risk_veto and risk.lean_hint == "HOLD":
            risk_veto = any(
                c.startswith(("NEWS_DAY", "EXPIRY", "cited_news", "BIG_NEWS"))
                for c in risk.citations
            )
    # Chain watcher soft veto on thin wall / fake breakout when no strong tech align
    watch_flag = str((ctx.chain_watch or {}).get("hypothesis_flag") or "NONE")
    if watch_flag in ("THIN_WALL_HYPOTHESIS", "BOTH_HYPOTHESIS") and session_kind == "NORMAL":
        if technical.lean_hint == "HOLD" or chain.lean_hint == "HOLD":
            risk_veto = risk_veto  # keep; lean may already be HOLD from chain

    lean = risk.lean_hint if lean_ok(risk.lean_hint) else "HOLD"
    if risk_veto:
        lean = "HOLD"
    # Handoff hygiene gaps are recorded — they must NOT kill CE/PE (founder:
    # agents/notes must not block when strategy/chain fires). Live orders stay refused.
    handoff_soft_gaps = list(handoff_errors)

    # When news veto is parked, prefer strategy / chain / tech CE|PE over soup HOLD.
    if lean == "HOLD" and not risk_veto and not news_veto_enabled():
        for cand in (technical.lean_hint, chain.lean_hint, trader.lean_hint):
            if lean_ok(cand) and cand in ("BUY_CE", "BUY_PE"):
                lean = cand
                break
        if lean == "HOLD" and ctx.chain_lean == "CE":
            lean = "BUY_CE"
        elif lean == "HOLD" and ctx.chain_lean == "PE":
            lean = "BUY_PE"

    stage: Stage
    if risk_veto:
        stage = "VETOED"
        lean = "HOLD"
    elif lean == "HOLD":
        stage = "WATCH"
    else:
        stage = "EARLY"  # v0: never CONFIRMED from agent loop alone

    vetoes = []
    if news_veto_enabled():
        vetoes = [
            c
            for c in risk.citations
            if c.startswith(
                (
                    "NEWS_DAY",
                    "EXPIRY",
                    "cited_news",
                    "BIG_NEWS",
                    "neutral_risk",
                    "MIX-CLOCK",
                    "PAPER_PAUSED",
                    "CALENDAR",
                )
            )
        ]
    # Soft chain flags are notes, not hard ticket killers while news veto is parked.
    if watch_flag != "NONE" and (news_veto_enabled() or watch_flag.startswith("NO_TRADE")):
        vetoes.append(f"chain_watcher:{watch_flag}")

    mix_lines = list((ctx.mix_inputs or {}).get("reason_lines") or [])
    reasons = [
        f"boss: {boss.summary[:180]}",
        f"tech: {technical.summary[:120]}",
        f"chain: {chain.summary[:120]}",
        f"bull: {bull.summary[:100]}",
        f"bear: {bear.summary[:100]}",
        f"trader: paper {trader.lean_hint} (execution refused)",
        f"news_veto_enabled={str(news_veto_enabled()).lower()}",
    ]
    reasons.extend(mix_lines[:8])
    if vetoes:
        reasons.extend(vetoes[:4])
    if watch_flag != "NONE" and f"chain_watcher:{watch_flag}" not in vetoes:
        reasons.append(f"chain_watcher:{watch_flag} (soft note — not a hard HOLD)")
    reasons.extend(handoff_soft_gaps[:4])

    gaps: list[str] = []
    for r in reports:
        gaps.extend(r.data_gaps)
    gaps.extend(ctx.data_gaps)
    gaps.extend(handoff_soft_gaps)
    seen = set()
    uniq_gaps = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            uniq_gaps.append(g)

    banner = top_veto_reasons(
        session_kind=session_kind, vetoes=vetoes, reasons=reasons, limit=3
    )
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
        data_gaps=uniq_gaps[:16],
        bull_summary=bull.summary,
        bear_summary=bear.summary,
        news_summary=news.summary,
        sentiment_summary=sentiment.summary,
        technical_summary=technical.summary,
        chain_watcher_summary=chain.summary,
        risk_summary=risk.summary,
        boss_summary=boss.summary,
        trader_summary=trader.summary,
        premium_lean=dict(ctx.premium_lean or {}),
        reports=[r.to_dict() for r in reports],
        handoffs=[h.to_dict() for h in handoffs],
        provenance=provenance,
        top_veto_reasons=banner,
        premarket_sentiment=dict(premarket),
        index_bars=list(ctx.index_bars),
        index_bar_meta=dict(ctx.index_bar_meta or {}),
    )


def run_session(
    *,
    underlyings: Optional[Sequence[str]] = None,
    dry_run: bool = True,
    use_llm: bool = False,
    prefer_desk: bool = False,
    gather_india_news: bool = False,
    prefer_live_chain: bool = False,
    persist: bool = True,
    mode: Optional[str] = None,
    settings: Optional[Settings] = None,
    clock_snapshot: Optional[dict[str, Any]] = None,
    session_id: str = "",
    run_id: str = "",
) -> SessionResult:
    settings = settings or load_settings()
    names = tuple(underlyings) if underlyings else settings.underlyings
    llm: Optional[LlmClient] = None
    openai_used = False
    session_gaps: list[str] = []
    mix_inputs = build_reason_inputs(settings.repo_root)

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
        if not llm.enabled:
            session_gaps.append(
                "DATA_INSUFFICIENT: --use-llm requested but OpenAI unavailable — rule fallback"
            )
            if llm.last_error:
                session_gaps.append(f"UNKNOWN: {llm.last_error}")
    elif not settings.openai_key_present:
        session_gaps.append("DATA_INSUFFICIENT: OPENAI_API_KEY not set in env/.env")

    tickets: list[PaperTicket] = []
    all_handoffs: list[dict[str, Any]] = []
    for name in names:
        ctx, gaps = _resolve_context(
            name,
            prefer_desk=prefer_desk,
            gather_india_news=gather_india_news,
            prefer_live_chain=prefer_live_chain,
            mix_inputs=mix_inputs,
        )
        session_gaps.extend(gaps)
        if use_llm:
            ctx = _attach_rag(ctx)
            session_gaps.extend(ctx.data_gaps)
        if llm is not None:
            llm.skip_all = False  # type: ignore[attr-defined]
        # Clock / calendar closed → skip LLM for this tick entirely.
        clock = clock_snapshot or {}
        if llm is not None and (
            clock.get("allow_directional_paper") is False
            or clock.get("in_dead_band") is True
            or not clock.get("in_session_shell", True)
        ):
            llm.skip_all = True  # type: ignore[attr-defined]
        ticket = run_underlying_session(
            ctx,
            settings,
            llm if use_llm else None,
            gather_india_news=gather_india_news,
        )
        tickets.append(ticket)
        all_handoffs.extend(ticket.handoffs)

    # Honest flag: only true when at least one OpenAI JSON call succeeded this tick.
    if llm is not None and llm.success_count > 0:
        openai_used = True
    elif use_llm and llm is not None and llm.fail_count > 0 and llm.last_error:
        session_gaps.append(
            f"DATA_INSUFFICIENT: OpenAI enabled but no successful call "
            f"(last_error_class={llm.last_error_class})"
        )

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
        handoffs=all_handoffs,
        clock=dict(clock_snapshot or {}),
        mix_inputs=mix_inputs,
        session_id=session_id,
        run_id=run_id,
    )

    if persist:
        kb = AgentKB(settings.kb_path)
        kb.save_session(result.to_dict())

    return result
