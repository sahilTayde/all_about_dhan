"""V2 strategy plugin API (architecture §2.5). Paper only; never places orders.

`StrikeChoice` / `StrikeQuote` and the `ExitPlan` primitives are the V2-01 / V2-06b
definitions from `contracts.payloads` — this module re-exports them so there is a
single type. Do not add a second StrikeChoice here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from contracts.payloads import (
    AtrStop,
    CatastrophicStop,
    ExitPlan,
    GracePeriod,
    Level,
    Partial,
    SignalFlipExit,
    StrikeChoice,
    StrikeQuote,
    StructuralStop,
    TimeStop,
    Trail,
)

from .feature_view_stub import FeatureView

__all__ = [
    "AtrStop",
    "Bar",
    "CatastrophicStop",
    "ChainSnapshot",
    "EntryPolicy",
    "ExitPlan",
    "ExitRequest",
    "GracePeriod",
    "Level",
    "Partial",
    "PositionUpdate",
    "SessionContext",
    "Signal",
    "SignalFlipExit",
    "Strategy",
    "StrategyMeta",
    "StrikeChoice",
    "StrikeQuote",
    "StructuralStop",
    "TimeStop",
    "Trail",
]


@dataclass(frozen=True)
class EntryPolicy:
    """How the desk may enter (founder addendum 6). Default is chase."""

    mode: str = "chase"  # "chase" | "pullback_limit" | "wait_consolidation"
    zones: tuple[str, ...] = ("fvg", "candle_50")
    max_chase_ticks: int = 2
    chase_timeout_s: float = 2.0
    chase_calibration: str = "chase_defaults@unversioned"


@dataclass(frozen=True)
class StrategyMeta:
    """Strategy metadata checked at load. Never STRAT-015+."""

    strategy_id: str
    version: str
    params_hash: str
    markets: tuple[str, ...]
    underlyings: tuple[str, ...]
    inputs: tuple[str, ...]
    features: tuple[str, ...]
    stage: str  # "shadow" | "paper" | "live_eligible"
    max_positions: int = 1
    entry_policy: EntryPolicy = field(default_factory=EntryPolicy)
    legacy_logic_from: tuple[str, ...] = ()


@dataclass(frozen=True)
class Signal:
    """Strategy-emitted signal (plugins emit signals, never orders)."""

    signal_id: str
    strategy_id: str
    underlying: str
    side: str  # "CE" | "PE"
    strike_rule: str
    strike_choice: StrikeChoice
    decision_ts: str
    confidence: float
    exit_plan: ExitPlan
    reasons: tuple[str, ...]
    features: dict[str, float]


@dataclass(frozen=True)
class SessionContext:
    """Passed to `on_session_start`."""

    session_date: str
    market: str
    config: dict[str, Any]


@dataclass(frozen=True)
class Bar:
    """Closed OHLCV bar stub (real bars come from V2-03)."""

    instrument_id: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: str
    available_ts: str
    gap: bool = False


@dataclass(frozen=True)
class ChainSnapshot:
    """Option-chain snapshot stub."""

    timestamp: str
    underlying: str
    strikes: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class PositionUpdate:
    """Position update stub."""

    instrument_id: str
    net_qty: int
    avg_price: float
    unrealized_pnl: float


@dataclass(frozen=True)
class ExitRequest:
    """Optional strategy-initiated exit."""

    position_id: str
    reason: str
    urgency: str = "normal"


class Strategy(Protocol):
    """Plugin protocol. Runtime loads by module path and checks meta."""

    meta: StrategyMeta
    exit_plan: ExitPlan

    def on_session_start(self, ctx: SessionContext) -> None: ...

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]: ...

    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]: ...

    def on_position(self, update: PositionUpdate) -> list[ExitRequest]: ...

    def on_session_end(self) -> dict[str, Any]: ...
