"""Hooks package (desk, event memory, India news, chain, premium, depth, rag)."""

from trading_agents_india.hooks.chain import watch_chain
from trading_agents_india.hooks.depth import fetch_depth_snapshot
from trading_agents_india.hooks.desk import try_load_desk_context
from trading_agents_india.hooks.event_memory import (
    classify_session_kind,
    news_item_severity,
    news_veto_enabled,
    score_premarket_sentiment,
    top_veto_reasons,
)
from trading_agents_india.hooks.news import gather_news, try_dhan_news
from trading_agents_india.hooks.index_bars import fetch_index_bars
from trading_agents_india.hooks.premium import resolve_premium_lean
from trading_agents_india.hooks.rag import fetch_rag_context

__all__ = [
    "try_load_desk_context",
    "classify_session_kind",
    "news_item_severity",
    "news_veto_enabled",
    "score_premarket_sentiment",
    "top_veto_reasons",
    "gather_news",
    "try_dhan_news",
    "watch_chain",
    "resolve_premium_lean",
    "fetch_index_bars",
    "fetch_depth_snapshot",
    "fetch_rag_context",
]
