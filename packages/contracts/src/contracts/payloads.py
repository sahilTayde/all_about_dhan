"""Payload dataclasses for V2 events."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DepthQuote:
    """DEPTH_QUOTE payload: 5-level bid/ask depth."""

    instrument_id: str
    bid: float | None
    bid_qty: int | None
    ask: float | None
    ask_qty: int | None
    ltp: float | None
    oi: int | None
    levels: dict[str, list[list[float | int]]]  # {"bid": [[price, qty], ...], "ask": [[price, qty], ...]}
    exchange_ts: str
    repeat: bool = False
    raw_b64: str | None = None


@dataclass(frozen=True)
class QuoteSnapshot:
    """QUOTE_SNAPSHOT payload: bid/ask snapshot every 5s."""

    instrument_id: str
    rule: str  # "ATM" | "ITM100" | "ITM200"
    side: str  # "CE" | "PE"
    bid: float | None
    ask: float | None
    mid: float | None
    spread: float | None
    ltp: float | None
    ltt: str | None  # last trade time
    oi: int | None
    depth_age_ms: int | None
    stale: bool = False


@dataclass(frozen=True)
class OiCadence:
    """OI_CADENCE payload: OI update frequency per instrument."""

    instrument_id: str
    window_s: int
    oi_updates: int
    median_gap_s: float | None
    p90_gap_s: float | None
    last_oi_change: str | None
    sources: list[str]


@dataclass(frozen=True)
class Level:
    """Price level: premium or underlying."""

    kind: str  # "premium" | "underlying"
    price: float


@dataclass(frozen=True)
class CatastrophicStop:
    """Catastrophic stop (required on every strategy)."""

    level: Level


@dataclass(frozen=True)
class StructuralStop:
    """Structural stop: beyond the structure that defines the idea."""

    level: Level
    trigger: str = "bar_close"  # "bar_close" | "tick"


@dataclass(frozen=True)
class AtrStop:
    """ATR-based stop."""

    k: float
    trigger: str = "bar_close"


@dataclass(frozen=True)
class TimeStop:
    """Time-based stop."""

    after_s: int
    when: str = "always"  # "always" | "entry_in:09:15-10:00" | "expiry_day" | etc
    unless_profit_pts: float | None = None


@dataclass(frozen=True)
class GracePeriod:
    """Grace period: blocks exits except catastrophic, EOD, founder."""

    seconds: int


@dataclass(frozen=True)
class SignalFlipExit:
    """Exit on signal flip."""

    on: tuple[str, ...] = ("own_opposite",)  # "own_opposite" | "boss_opposite"
    trigger: str = "bar_close"


@dataclass(frozen=True)
class Partial:
    """Partial exit at target."""

    at: Level
    fraction: float


@dataclass(frozen=True)
class Trail:
    """Trailing stop."""

    kind: str  # "step" | "percent"
    activate_at: Level
    step: float | None = None
    percent: float | None = None


@dataclass(frozen=True)
class ExitPlan:
    """Complete exit plan for a strategy."""

    catastrophic: CatastrophicStop
    structural: StructuralStop | None = None
    atr: AtrStop | None = None
    time_stops: tuple[TimeStop, ...] = ()
    grace: GracePeriod | None = None
    signal_flip: SignalFlipExit | None = None
    target: Level | None = None
    partials: tuple[Partial, ...] = ()
    trail: Trail | None = None
    flat_by_ist: str = "15:15"
    defaults_from: str | None = None


@dataclass(frozen=True)
class StrikeQuote:
    """Strike quote with pricing info."""

    rule: str  # "ATM" | "ITM100" | "ITM200"
    instrument_id: str
    bid: float | None
    ask: float | None
    mid: float | None
    spread: float | None
    quote_age_ms: int | None
    est_delta: float | None
    est_round_trip_pts: float | None


@dataclass(frozen=True)
class StrikeChoice:
    """Strike router choice with alternatives."""

    chosen: str  # "ATM" | "ITM100" | "ITM200"
    reason: str
    rule_version: str
    alternatives: tuple[StrikeQuote, ...]
