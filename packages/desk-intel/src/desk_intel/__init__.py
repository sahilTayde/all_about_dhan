"""Morning news + DhanHQ option-chain fusion → MARKET_SIGNAL (bias, not advice)."""

from desk_intel.workspace import ensure_repo_on_path

ensure_repo_on_path()

from desk_intel.fusion import fuse
from desk_intel.news_ingest import ingest_news
from desk_intel.option_chain_poller import compute_chain_bias, poll_underlyings
from desk_intel.outcomes import OUTCOME_HELP, still_valid
from desk_intel.schema import COMPLIANCE_NOTE, MarketSignal, NewsEvent, SignalOutcome

__all__ = [
    "COMPLIANCE_NOTE",
    "OUTCOME_HELP",
    "MarketSignal",
    "NewsEvent",
    "SignalOutcome",
    "compute_chain_bias",
    "fuse",
    "ingest_news",
    "poll_underlyings",
    "still_valid",
]
