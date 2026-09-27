"""V2 broker factory: paper is the only constructible broker. Live path is sealed."""

from __future__ import annotations

from typing import Any

from brokers.fills import ClockedPaperBroker
from brokers.orders import LiveOrderRefused

V2_LIVE_BROKERS_ENABLED = False


class LiveBrokerDisabled(LiveOrderRefused):
    """V2 paper-only: live/Dhan construction is refused and cannot be enabled from tests."""


def live_brokers_enabled() -> bool:
    """Always False. Not overridable by env, config, or tests."""
    return V2_LIVE_BROKERS_ENABLED


def make_broker(
    *, mode: str = "paper", clock: Any, **kwargs: Any
) -> ClockedPaperBroker:
    """Return a clocked paper broker. Any non-paper mode fails closed."""
    if mode != "paper" or live_brokers_enabled():
        raise LiveBrokerDisabled(
            f"V2 paper-only: broker mode {mode!r} is disabled and cannot be enabled "
            "from tests or default config"
        )
    if "cost_model" in kwargs:
        raise LiveBrokerDisabled(
            "V2 has no cost_model switch; realistic fills are the only mode"
        )
    return ClockedPaperBroker(clock=clock, **kwargs)
