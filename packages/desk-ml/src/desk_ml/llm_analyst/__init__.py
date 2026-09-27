"""LLM analyst (PR-016). ADVISORY ONLY, paper only: returns a verdict, never an order.

This package must not import the broker, desk, risk engine, ledger, Dhan client, or the paper
engine's order path; tests/test_llm_analyst.py enforces that.
"""

from desk_ml.llm_analyst.advisor import Advisor, get_advisor, load_config, reset_advisors
from desk_ml.llm_analyst.context import build_context, context_hash, scrub, untrusted_text
from desk_ml.llm_analyst.providers import (
    PROMPT_VERSION, PROVIDERS, VERDICT_SCHEMA, MockProvider, OpenAIProvider, Provider, ProviderError,
    RecordedProvider, Reply, VerdictError, make_provider, parse_verdict,
)

__all__ = [
    "PROMPT_VERSION", "PROVIDERS", "VERDICT_SCHEMA", "Advisor", "MockProvider", "OpenAIProvider", "Provider",
    "ProviderError", "RecordedProvider", "Reply", "VerdictError", "build_context", "context_hash", "get_advisor",
    "load_config", "make_provider", "parse_verdict", "reset_advisors", "scrub", "untrusted_text",
]
