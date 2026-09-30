"""Shared dataclasses for the paper/replay exit lab."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Quote:
    """One available quote. `available_ts` is when the desk could see it."""

    available_ts: datetime
    bid: float | None
    ask: float | None
    ltp: float | None
    index: float | None = None
    iv: float | None = None
    strike: float | None = None
    side: str | None = None
    spread: float | None = None
    volume: float | None = None
    oi: float | None = None
    stale: bool = False
    source: str = "unknown"


@dataclass(frozen=True)
class Bar:
    """Closed 1m bar. Known only after `available_ts` (bar close)."""

    ts: datetime
    available_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    oi: float | None = None
    strike: float | None = None
    side: str | None = None
    index_open: float | None = None
    index_high: float | None = None
    index_low: float | None = None
    index_close: float | None = None
    iv: float | None = None


@dataclass(frozen=True)
class Entry:
    """One entry to judge exits against. Lots are whole lots."""

    entry_id: str
    ts: datetime
    side: str  # CE | PE
    strike: float
    entry_price: float
    lots: int
    lot_size: int
    entry_set: str
    session: str
    index_at_entry: float | None = None
    iv_at_entry: float | None = None
    atm_strike: float | None = None
    expiry: str | None = None
    moneyness: str = "ATM"
    scenario: str = "unknown"
    seed: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def qty(self) -> int:
        return int(self.lots) * int(self.lot_size)


@dataclass
class OpenState:
    """Mutable path state. Only updated with data at or before clock.now."""

    entry: Entry
    remaining_qty: int
    stop_premium: float | None = None
    target_premium: float | None = None
    trail_stop: float | None = None
    mfe: float = 0.0
    mae: float = 0.0
    mfe_index: float = 0.0
    mae_index: float = 0.0
    seen_high: float = 0.0
    seen_low: float = 0.0
    seen_high_ts: datetime | None = None
    last_bid: float | None = None
    last_ask: float | None = None
    last_ltp: float | None = None
    last_index: float | None = None
    last_iv: float | None = None
    last_quote_ts: datetime | None = None
    closed_bars: list[Bar] = field(default_factory=list)
    premium_prints: list[float] = field(default_factory=list)
    partials_done: int = 0
    realized_gross: float = 0.0
    realized_charges: float = 0.0
    legs: list[dict[str, Any]] = field(default_factory=list)
    skipped: str | None = None


@dataclass(frozen=True)
class Fill:
    side: str  # BUY | SELL
    ts: datetime
    qty: int
    price: float
    model: str
    reason: str


@dataclass(frozen=True)
class TradeResult:
    entry_id: str
    entry_set: str
    session: str
    scenario: str
    side: str
    strike: float
    lots: int
    qty: int
    entry_ts: str
    exit_ts: str | None
    entry_price: float
    exit_price: float | None
    exit_reason: str
    time_in_trade_s: float
    mfe: float
    mae: float
    mfe_inr: float
    mae_inr: float
    gross_inr: float
    charges_inr: float
    net_inr: float
    plan_id: str
    data_source: str
    skipped: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionLabel:
    session: str
    weekday: str
    expiry_day: bool
    day_before_expiry: bool
    scenario: str
    tags: tuple[str, ...]
    index_open: float | None
    index_close: float | None
    range_pts: float | None
    atr: float | None
    gap_pct: float | None
    atm_iv: float | None
    er: float | None
    feed_freeze: bool
    data_source: str
    notes: str = ""
