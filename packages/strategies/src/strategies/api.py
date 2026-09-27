"""
V2 strategy API (section 2.5 of V2_PRODUCTION_ARCHITECTURE).

Defines the core types for strategy plugins: StrategyMeta, TimeStop, ExitPlan,
Signal, and the Strategy protocol. All strategies emit signals, never orders.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from .feature_view_stub import FeatureView


@dataclass(frozen=True)
class Level:
    """Price level for stops, targets, trails."""

    kind: str  # "premium" | "underlying"
    price: float


@dataclass(frozen=True)
class Partial:
    """Partial exit specification."""

    at: Level
    fraction: float  # 0.0 to 1.0


@dataclass(frozen=True)
class Trail:
    """Trailing stop specification."""

    kind: str  # "step" | "percent"
    activate_at: Level
    step: float


@dataclass(frozen=True)
class TimeStop:
    """
    First-class exit primitive (V2-09).

    A time stop fires after a fixed number of seconds from the entry fill.
    Multiple time stops can be defined with different `when` conditions;
    the first matching condition at entry wins.
    """

    after_s: int  # seconds after entry fill
    when: str = "always"  # "always" | "entry_in:HH:MM-HH:MM" | "expiry_day" | composite
    unless_profit_pts: float | None = None  # optional: skip if premium up at least this much


@dataclass(frozen=True)
class ExitPlan:
    """
    Complete exit plan for a position.

    Exit order (section 2.9):
    1. Founder commands (KILL, flatten)
    2. Protective stop (catastrophic, disaster stop)
    3. EOD flat (15:15 IST by default)
    4. Time stops (first matching `when` at entry)
    5. Target and partials
    6. Trailing stop (modifies protective stop)
    7. Strategy exit requests

    Round 11 defaults (config/v2/exits/defaults.yaml):
    - catastrophic.max_loss = 30000 (₹30k house stop)
    - structural.enabled = true (each strategy must supply native invalidation)
    - All other primitives off
    """

    catastrophic_max_loss: int | None = None  # ₹ max loss (house stop); REQUIRED (REG-18d)
    structural_stop: Level | None = None  # strategy's native invalidation level
    stop: Level | None = None  # DEPRECATED: use structural_stop
    target: Level | None = None
    time_stops: tuple[TimeStop, ...] = ()
    flat_by_ist: str = "15:15"  # HH:MM IST; EOD flatten time
    partials: tuple[Partial, ...] = ()
    trail: Trail | None = None
    protective_stop: Level | None = None  # resting broker-side stop
    defaults_from: str | None = None  # sha256 of config/v2/exits/defaults.yaml (REG-13)


@dataclass(frozen=True)
class StrikeQuote:
    """Shadow-priced strike alternative (V2-06b)."""

    rule: str  # "ATM" | "ITM100" | "ITM200"
    instrument_id: str
    bid: float | None
    ask: float | None
    mid: float | None
    spread: float | None
    quote_age_ms: int | None  # age of QUOTE_SNAPSHOT/depth; None = no quote
    est_delta: float | None  # from chain or Black-76; tagged with source
    est_round_trip_pts: float | None  # charges + spread


@dataclass(frozen=True)
class StrikeChoice:
    """
    Strike router output (V2-06b).

    The router picks ATM, ITM100 or ITM200 based on rules-as-data:
    - No ATM on expiry day
    - 09:15-10:00 decay window
    - DTE rule
    - Lowest break-even move for the planned hold
    - STRATEGY_FIXED (strategy pins a strike)

    All three alternatives are shadow-priced at the same decision_ts
    (available_ts ≤ decision_ts only, for causality).
    """

    chosen: str  # "ATM" | "ITM100" | "ITM200"
    reason: str  # e.g. "EXPIRY_DAY_NO_ATM", "LOWEST_BREAKEVEN_AT_HOLD"
    rule_version: str  # router version + params hash (REG-13)
    alternatives: tuple[StrikeQuote, ...]  # all three, priced at same decision_ts


@dataclass(frozen=True)
class Signal:
    """
    Strategy signal output.

    Strategies emit signals, never orders. The boss and desk layers handle
    basket gating, conflicts, sizing, and execution.
    """

    signal_id: str  # ids.signal_id(strategy_id, version, underlying, decision_ts, n)
    strategy_id: str
    underlying: str  # "NIFTY" | "SENSEX" | "BANKNIFTY"
    side: str  # "CE" | "PE" (buyer-only desk; writer-side needs founder decision)
    strike_rule: str  # "ATM" | "ITM100" | "ITM200" | "ROUTER"
    strike_choice: StrikeChoice  # filled by StrikeRouter
    decision_ts: str  # ISO 8601, == clock.now() when emitted
    confidence: float  # 0..1, calibrated or null; never shown as win rate
    exit_plan: ExitPlan
    reasons: tuple[str, ...]  # machine codes + one human line
    features: dict[str, float]  # exact inputs used (audit + forward evaluator)


@dataclass(frozen=True)
class StrategyMeta:
    """
    Strategy metadata and constraints.

    Every strategy declares its id, version, markets, features, and stage.
    The runtime checks these at load time and refuses incompatible strategies.
    """

    strategy_id: str  # "R8-E1-COIL-SIDE", "TEST-CROSS", "MIX-..." (never STRAT-015+)
    version: str  # semver; bump on any logic change
    params_hash: str  # sha256 of frozen params (REG-13: includes exit plan)
    markets: tuple[str, ...]  # ("IN_INDEX_OPT",) now; ("FX_SPOT",) later
    underlyings: tuple[str, ...]  # ("NIFTY", "SENSEX")
    inputs: tuple[str, ...]  # ("bars:1m", "chain", "depth")
    features: tuple[str, ...]  # feature names it reads (checked at load)
    stage: str  # "shadow" | "paper" | "live_eligible"
    max_positions: int = 1


@dataclass(frozen=True)
class SessionContext:
    """Context provided to strategies at session start."""

    session_date: str  # YYYY-MM-DD
    market: str  # "IN_INDEX_OPT"
    config: dict[str, Any]  # market-specific config


@dataclass(frozen=True)
class Bar:
    """OHLCV bar (minimal stub; real version in V2-03)."""

    instrument_id: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: str  # ISO 8601
    available_ts: str  # ISO 8601, when bar closed
    gap: bool = False


@dataclass(frozen=True)
class ChainSnapshot:
    """Option chain snapshot (minimal stub)."""

    timestamp: str  # ISO 8601
    underlying: str
    strikes: tuple[dict[str, Any], ...]  # strike dicts with CE/PE data


@dataclass(frozen=True)
class PositionUpdate:
    """Position update (minimal stub)."""

    instrument_id: str
    net_qty: int
    avg_price: float
    unrealized_pnl: float


@dataclass(frozen=True)
class ExitRequest:
    """Strategy-initiated exit request."""

    position_id: str
    reason: str
    urgency: str = "normal"  # "normal" | "urgent"


class Strategy(Protocol):
    """
    Strategy plugin protocol.

    All strategy plugins must implement this protocol. The runtime loads
    strategies by module path and checks declared features/markets.
    """

    meta: StrategyMeta

    def on_session_start(self, ctx: SessionContext) -> None:
        """Called once at session start."""
        ...

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]:
        """Called on each closed bar."""
        ...

    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]:
        """Called on each chain snapshot."""
        ...

    def on_position(self, update: PositionUpdate) -> list[ExitRequest]:
        """Optional: called on position updates for early exits."""
        ...

    def on_session_end(self) -> dict[str, Any]:
        """Called at session end; return per-strategy day stats."""
        ...
