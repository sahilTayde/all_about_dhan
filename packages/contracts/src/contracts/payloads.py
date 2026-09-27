"""Payload dataclasses for V2 events (section 4.4 complete type set)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ============================================================================
# Market Data Payloads
# ============================================================================


@dataclass(frozen=True)
class Tick:
    """TICK payload (md:ticks)."""

    instrument_id: str
    ltp: float | None
    ltq: int | None
    volume: int | None
    oi: int | None
    exchange_ts: str


@dataclass(frozen=True)
class DepthQuote:
    """DEPTH_QUOTE payload (md:depth): 5-level bid/ask depth."""

    instrument_id: str
    bid: float | None
    bid_qty: int | None
    ask: float | None
    ask_qty: int | None
    ltp: float | None
    oi: int | None
    levels: dict[
        str, list[list[float | int]]
    ]  # {"bid": [[price, qty], ...], "ask": [[price, qty], ...]}
    exchange_ts: str
    repeat: bool = False
    raw_b64: str | None = None


@dataclass(frozen=True)
class QuoteSnapshot:
    """QUOTE_SNAPSHOT payload (md:quotes): bid/ask snapshot every 5s."""

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
    """OI_CADENCE payload (md:oi_cadence): OI update frequency per instrument."""

    instrument_id: str
    window_s: int
    oi_updates: int
    median_gap_s: float | None
    p90_gap_s: float | None
    last_oi_change: str | None
    sources: list[str]


@dataclass(frozen=True)
class BarClosed:
    """BAR_CLOSED payload (md:bars:1m, md:bars:3m, md:bars:5m)."""

    instrument_id: str
    tf: str  # "1m" | "3m" | "5m"
    start: str  # ISO-8601
    end: str  # ISO-8601
    o: float | None
    h: float | None
    l: float | None  # noqa: E741 (OHLC standard)
    c: float | None
    v: int | None  # volume
    n_ticks: int
    gap: bool = False
    late_ticks: int = 0


@dataclass(frozen=True)
class ChainOptionData:
    """Option data within chain snapshot."""

    ltp: float | None = None
    bid: float | None = None
    ask: float | None = None
    oi: int | None = None
    oi_chg: int | None = None
    iv: float | None = None
    volume: int | None = None


@dataclass(frozen=True)
class ChainStrike:
    """Strike data within chain snapshot."""

    strike: float
    ce: ChainOptionData
    pe: ChainOptionData


@dataclass(frozen=True)
class ChainSnapshot:
    """CHAIN_SNAPSHOT payload (md:chain)."""

    underlying: str
    expiry: str
    spot: float
    strikes: list[ChainStrike]


@dataclass(frozen=True)
class Clock:
    """CLOCK payload (md:clock): 1s heartbeat."""

    session: str  # YYYY-MM-DD
    phase: str  # "PRE_OPEN" | "MARKET" | "POST_CLOSE" | "CLOSED"
    minute: str  # HH:MM


@dataclass(frozen=True)
class FeedStatus:
    """FEED_STATUS payload (md:status)."""

    status: str  # "UP" | "DOWN" | "STALE"
    instrument_id: str | None = None
    since: str | None = None
    gap_s: float | None = None


# ============================================================================
# Strategy & Decision Payloads
# ============================================================================


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


@dataclass(frozen=True)
class Signal:
    """SIGNAL payload (sig:signals)."""

    signal_id: str
    strategy_id: str
    version: str
    params_hash: str
    stage: str  # "shadow" | "paper" | "live_eligible"
    underlying: str
    side: str  # "CE" | "PE"
    strike_rule: str  # "ATM" | "ITM100" | "ITM200" | "ROUTER"
    decision_ts: str
    confidence: float | None
    exit_plan: dict[str, Any]  # ExitPlan as dict
    strike_choice: dict[str, Any]  # StrikeChoice as dict
    reasons: list[str]
    features: dict[str, float]


@dataclass(frozen=True)
class ZoneDistance:
    """Zone distance for entry location."""

    zone: str  # "fvg" | "candle_50" | "vwap" | "ema20" | "poc"
    price: float
    distance_atr: float
    source: str


@dataclass(frozen=True)
class EntryLocation:
    """Entry location analysis."""

    signal_candle_atr: float
    signal_body_atr: float
    entry_distance_atr: float | None
    atr: float
    spot: float
    nearest: dict[str, Any] | None  # ZoneDistance as dict
    zones: list[dict[str, Any]]  # list of ZoneDistance as dict


@dataclass(frozen=True)
class Decision:
    """DECISION payload (boss:decisions)."""

    decision_id: str
    underlying: str
    decision: str  # "ENTER" | "HOLD"
    signal_ids: list[str]
    instrument_id: str | None = None
    lots: int | None = None
    lot_size: int | None = None
    limit_price: float | None = None
    sizing: dict[str, int] | None = None
    holds: list[str] = ()  # type: ignore[assignment]
    basket_hash: str | None = None
    shadow: dict[str, Any] | None = None
    entry_location: dict[str, Any] | None = None  # EntryLocation as dict
    stretch: dict[str, Any] | None = None


@dataclass(frozen=True)
class EntryPlan:
    """ENTRY_PLAN payload (oms:plans)."""

    plan_id: str
    decision_id: str
    signal_id: str
    account_id: str
    action: str  # "CHASE" | "LIMIT" | "WAIT"
    shadow_actions: list[str]
    stretch: dict[str, float]
    zone: str | None
    zone_price: float | None
    entry_distance_atr: float | None
    signal_candle_atr: float
    limit_price: float
    est_delta: float | None
    expires_at: str
    client_order_id: str


@dataclass(frozen=True)
class EntryPlanResult:
    """ENTRY_PLAN_RESULT payload (oms:plans)."""

    plan_id: str
    status: str  # "FILLED" | "MISSED" | "CANCELLED"
    fill_price: float | None = None
    filled_at: str | None = None
    waited_s: float | None = None
    giveback_5m_pts: float | None = None
    giveback_5m_atr: float | None = None
    shadow: dict[str, Any] | None = None


# ============================================================================
# Order & Position Payloads
# ============================================================================


@dataclass(frozen=True)
class RiskDecision:
    """RISK_DECISION payload (oms:risk)."""

    client_order_id: str
    action: str  # "ENTRY" | "EXIT"
    approved: bool
    reason_code: str | None
    reason: str | None
    critical: bool = False
    ticket_risk_inr: float | None = None


@dataclass(frozen=True)
class OrderUpdate:
    """ORDER_UPDATE payload (oms:orders)."""

    client_order_id: str
    broker_order_id: str
    account_id: str
    from_state: str
    to_state: str
    reason: str
    purpose: str  # "ENTRY" | "STOP" | "EXIT"


@dataclass(frozen=True)
class Fill:
    """FILL payload (oms:fills)."""

    client_order_id: str
    qty: int
    price: float
    fill_model: str  # "depth" | "ltp_slippage"
    quote_available_ts: str | None
    charges_inr: float | None


@dataclass(frozen=True)
class PositionUpdate:
    """POSITION_UPDATE payload (pos:updates)."""

    position_id: str
    account_id: str
    instrument_id: str
    net_qty: int
    avg_price: float
    mark: float
    unrealized_inr: float
    stop: dict[str, Any]  # Level as dict
    protective_order: str | None
    strategy_id: str


@dataclass(frozen=True)
class PositionClosed:
    """POSITION_CLOSED payload (pos:updates)."""

    position_id: str
    exit_reason: str
    gross_inr: float
    charges_inr: float
    net_inr: float
    held_s: int
    trade_id: str


# ============================================================================
# Control & Monitoring Payloads
# ============================================================================


@dataclass(frozen=True)
class FounderCommand:
    """FOUNDER_COMMAND payload (ctl:commands)."""

    command_id: str
    account_id: str
    kind: str  # "CUT_LOSS" | "FLATTEN" | "KILL" | "REARM" | "PAUSE" | "RESUME"
    args: dict[str, Any]
    actor: str
    reason: str | None
    confirm_token: str | None


@dataclass(frozen=True)
class CommandAck:
    """COMMAND_ACK payload (ctl:acks)."""

    command_id: str
    status: str  # "applied" | "rejected"
    applied_ts: str | None
    reason: str | None


@dataclass(frozen=True)
class Advice:
    """ADVICE payload (llm:advice)."""

    decision_id: str
    verdict: str  # "agree" | "disagree" | "abstain"
    reasons: list[str]
    provider: str
    prompt_version: str
    cost_usd: float
    context_hash: str


@dataclass(frozen=True)
class EngineStatus:
    """ENGINE_STATUS payload (health:engine)."""

    role: str
    status: str  # "STARTING" | "READY" | "DEGRADED" | "HALTED"
    session: str
    code_version: str
    config_hash: str
    basket_hash: str | None
    restart: bool
    input_lag_ms: int
