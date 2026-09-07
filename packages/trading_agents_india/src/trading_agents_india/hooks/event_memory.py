"""News / EVENT_MEMORY alignment hooks.

Customer-ticket policy (2026-09-07 process fix + founder simplify):
  - Soft-default: ``NEWS_VETO_ENABLED=false`` → news does **not** HOLD the
    customer paper ticket (notes / analog only). Re-enable with env true.
  - When enabled: mid-session hard HOLD/VETO only on BIG_NEWS (or EXPIRY /
    NO_TRADE halt). Routine / fixture / soft MACRO = pre-market sentiment.
  - News never deletes STRATs (KEEP_ALL). Never claimed alpha.
"""

from __future__ import annotations

import os
from typing import Iterable, Literal, Optional

from trading_agents_india.fixtures import MarketContext, NewsItem
from trading_agents_india.schemas import SessionKind

NewsSeverity = Literal["BIG_NEWS", "ROUTINE", "SOFT"]

# Mid-session customer-ticket veto — explicit big-news only (when enabled).
BIG_NEWS_TAGS = frozenset(
    {
        "BIG_NEWS",
        "WAR",
        "CIRCUIT",
        "HALT",
        "CRASH",
        "FOMC_PRINT",
        "CPI_PRINT",
        "RBI_POLICY",
        "BUDGET_DAY",
        "GEOPOLITICAL_SHOCK",
    }
)

# Soft / calendar stamps — pre-market sentiment only (not mid-session veto).
SOFT_MACRO_TAGS = frozenset(
    {"MACRO_EVENT", "NEWS_DAY", "CPI", "FED", "RBI", "CRUDE", "EIA", "MPC"}
)

ROUTINE_TAGS = frozenset({"FIXTURE", "ROUTINE", "PREMARKET_CONTEXT"})


def news_veto_enabled() -> bool:
    """Soft-default OFF. Founder parked news HOLD on paper customer path.

    Set NEWS_VETO_ENABLED=true|1|yes|on to restore BIG_NEWS / NEWS_DAY holds.
    """
    raw = (os.environ.get("NEWS_VETO_ENABLED") or "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def news_item_severity(item: NewsItem) -> NewsSeverity:
    """Classify one headline for customer-ticket gate.

    BIG_NEWS → mid-session HOLD/VETO **only when** news_veto_enabled().
    ROUTINE → fixture / dry overlay — never veto.
    SOFT → live-ish macro without BIG_NEWS tag — pre-market sentiment only.
    """
    tags = {str(t).upper() for t in (item.tags or [])}
    if tags & BIG_NEWS_TAGS:
        return "BIG_NEWS"
    if str(item.risk_bias or "").upper() == "NO_TRADE":
        return "BIG_NEWS"
    if tags & ROUTINE_TAGS:
        return "ROUTINE"
    if tags & SOFT_MACRO_TAGS:
        return "SOFT"
    return "SOFT"


def big_news_items(news: Iterable[NewsItem]) -> list[NewsItem]:
    return [n for n in news if news_item_severity(n) == "BIG_NEWS"]


def soft_news_items(news: Iterable[NewsItem]) -> list[NewsItem]:
    """Non-veto headlines for pre-market / soft sentiment context."""
    return [n for n in news if news_item_severity(n) != "BIG_NEWS"]


def score_premarket_sentiment(news: Iterable[NewsItem]) -> dict[str, object]:
    """Pre-market path: gather/score impact without holding the live ticket.

    Returns a soft label + cited headlines. Not alpha. Not a win rate.
    """
    items = list(news)
    big = big_news_items(items)
    soft = soft_news_items(items)
    risk_offs = sum(1 for n in soft if str(n.risk_bias).upper() == "RISK_OFF")
    risk_ons = sum(1 for n in soft if str(n.risk_bias).upper() == "RISK_ON")
    if big:
        label = "BIG_NEWS_HOLD" if news_veto_enabled() else "BIG_NEWS_NOTED"
        bias = "NO_TRADE" if news_veto_enabled() else "MIXED"
    elif risk_offs > risk_ons and risk_offs > 0:
        label = "SOFT_RISK_OFF"
        bias = "RISK_OFF"
    elif risk_ons > risk_offs and risk_ons > 0:
        label = "SOFT_RISK_ON"
        bias = "RISK_ON"
    elif soft:
        label = "SOFT_MIXED"
        bias = "MIXED"
    else:
        label = "QUIET"
        bias = "MIXED"
    return {
        "label": label,
        "bias": bias,
        "big_news_count": len(big),
        "soft_news_count": len(soft),
        "headlines": [n.headline for n in (big + soft)[:6]],
        "news_veto_enabled": news_veto_enabled(),
        "note": (
            "Pre-market sentiment / impact context only. "
            + (
                "Mid-session hard veto requires BIG_NEWS."
                if news_veto_enabled()
                else "NEWS_VETO_ENABLED=false — news does not HOLD the paper ticket."
            )
            + " Not a fill. Not alpha."
        ),
        "layer": "HYPOTHESIS",
    }


def classify_session_kind(news: Iterable[NewsItem], hint: str = "NORMAL") -> SessionKind:
    """Align with EVENT_MEMORY — but customer NEWS_DAY only on BIG_NEWS.

    EXPIRY hint still forces EXPIRY.
    NEWS_DAY hint alone does **not** force a hold when headlines are only
    fixture/routine/soft macro; those stay NORMAL with soft sentiment context.
    Empty news + explicit NEWS_DAY hint → NEWS_DAY (calendar-forced day).
    Tagging NEWS_DAY for analog is fine even when NEWS_VETO_ENABLED=false —
    the pipeline must not HOLD solely from that tag while the flag is off.
    """
    hint_u = (hint or "NORMAL").upper()
    if hint_u == "EXPIRY":
        return "EXPIRY"

    items = list(news)
    if big_news_items(items):
        return "NEWS_DAY"

    if hint_u == "NEWS_DAY":
        if not items:
            return "NEWS_DAY"
        # Hint present but only routine/soft fixtures → do not kill the ticket.
        return "NORMAL"

    return "NORMAL"


def news_hold_reasons(ctx: MarketContext, session_kind: SessionKind) -> list[str]:
    """Ticket hold reasons. Never a catalog delete. Never claimed alpha.

    When NEWS_VETO_ENABLED=false, emit notes only — do not phrase as hard HOLD.
    """
    reasons: list[str] = []
    if not news_veto_enabled():
        if session_kind == "NEWS_DAY" or big_news_items(ctx.news):
            reasons.append(
                "news_noted: BIG_NEWS/NEWS_DAY present but NEWS_VETO_ENABLED=false "
                "(parked — does not HOLD paper ticket)"
            )
        soft = soft_news_items(ctx.news)
        if soft:
            reasons.append(
                f"premarket_sentiment: {score_premarket_sentiment(soft).get('label')} "
                "(soft context — not a mid-session veto)"
            )
        return reasons

    if session_kind == "NEWS_DAY":
        reasons.append(
            "BIG_NEWS: hold customer ticket (SIGNAL_FUSION / EVENT_MEMORY) — not alpha"
        )
    if session_kind == "EXPIRY":
        reasons.append("EXPIRY: gamma/pin risk — no EARLY promote from agent loop")
    for item in big_news_items(ctx.news):
        reasons.append(f"cited_news: {item.headline} ({item.source_url})")
    # Soft/routine context is citation-only when not vetoing — never a hard hold string.
    if session_kind == "NORMAL":
        soft = soft_news_items(ctx.news)
        if soft:
            reasons.append(
                f"premarket_sentiment: {score_premarket_sentiment(soft).get('label')} "
                "(soft context — not a mid-session veto)"
            )
    return reasons


def top_veto_reasons(
    *,
    session_kind: SessionKind,
    vetoes: Optional[Iterable[str]] = None,
    reasons: Optional[Iterable[str]] = None,
    limit: int = 3,
) -> list[str]:
    """Customer-facing top veto / hold reasons (no indicator soup)."""
    out: list[str] = []
    for src in (vetoes or [], reasons or []):
        for raw in src:
            text = str(raw or "").strip()
            if not text:
                continue
            # Keep boss/tech/chain/bull/bear chatter off the customer banner.
            if text.startswith(
                ("boss:", "tech:", "chain:", "bull:", "bear:", "trader:", "input_mix:", "phd_note:")
            ):
                continue
            if text not in out:
                out.append(text)
            if len(out) >= limit:
                return out[:limit]
    if news_veto_enabled() and session_kind in ("NEWS_DAY", "EXPIRY") and not out:
        out.append(
            "BIG_NEWS hold"
            if session_kind == "NEWS_DAY"
            else "EXPIRY hold — no EARLY promote"
        )
    return out[:limit]


def analog_memory_note() -> str:
    return (
        "EVENT_MEMORY ANALOG_MEMORY: empty / DATA_INSUFFICIENT — do not invent path P/L"
    )
