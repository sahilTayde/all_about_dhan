"""News / EVENT_MEMORY alignment hooks. News holds ticket; does not fake alpha."""

from __future__ import annotations

from typing import Iterable

from trading_agents_india.fixtures import MarketContext, NewsItem
from trading_agents_india.schemas import SessionKind


MACRO_TAGS = frozenset({"MACRO_EVENT", "NEWS_DAY", "CPI", "FED", "RBI", "WAR", "CIRCUIT"})


def classify_session_kind(news: Iterable[NewsItem], hint: str = "NORMAL") -> SessionKind:
    """Align with desk RETUNE_GATE / EVENT_MEMORY: NEWS_DAY vs NORMAL vs EXPIRY."""
    if (hint or "").upper() == "EXPIRY":
        return "EXPIRY"
    if (hint or "").upper() == "NEWS_DAY":
        return "NEWS_DAY"
    for item in news:
        tags = {t.upper() for t in (item.tags or [])}
        if tags & MACRO_TAGS or item.risk_bias == "NO_TRADE":
            return "NEWS_DAY"
        if item.risk_bias == "RISK_OFF" and "MACRO_EVENT" in tags:
            return "NEWS_DAY"
    return "NORMAL"


def news_hold_reasons(ctx: MarketContext, session_kind: SessionKind) -> list[str]:
    """Ticket hold reasons. Never a catalog delete. Never claimed alpha."""
    reasons: list[str] = []
    if session_kind == "NEWS_DAY":
        reasons.append(
            "NEWS_DAY / MACRO_EVENT: hold customer ticket (SIGNAL_FUSION / EVENT_MEMORY) — not alpha"
        )
    if session_kind == "EXPIRY":
        reasons.append("EXPIRY: gamma/pin risk — no EARLY promote from agent loop")
    for item in ctx.news:
        if "MACRO_EVENT" in (item.tags or []) or session_kind == "NEWS_DAY":
            reasons.append(f"cited_news: {item.headline} ({item.source_url})")
    return reasons


def analog_memory_note() -> str:
    return (
        "EVENT_MEMORY ANALOG_MEMORY: empty / DATA_INSUFFICIENT — do not invent path P/L"
    )
