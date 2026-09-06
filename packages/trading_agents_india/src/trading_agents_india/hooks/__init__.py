"""Hooks package (desk, event memory, India news)."""

from trading_agents_india.hooks.desk import try_load_desk_context
from trading_agents_india.hooks.event_memory import classify_session_kind
from trading_agents_india.hooks.news import gather_news, try_dhan_news

__all__ = [
    "try_load_desk_context",
    "classify_session_kind",
    "gather_news",
    "try_dhan_news",
]
