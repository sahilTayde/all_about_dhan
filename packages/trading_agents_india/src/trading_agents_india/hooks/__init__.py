"""Hooks package (desk, event memory, India news, chain, premium)."""

from trading_agents_india.hooks.chain import watch_chain
from trading_agents_india.hooks.desk import try_load_desk_context
from trading_agents_india.hooks.event_memory import classify_session_kind
from trading_agents_india.hooks.news import gather_news, try_dhan_news
from trading_agents_india.hooks.premium import resolve_premium_lean

__all__ = [
    "try_load_desk_context",
    "classify_session_kind",
    "gather_news",
    "try_dhan_news",
    "watch_chain",
    "resolve_premium_lean",
]
