"""Vendored payload types for V2-D2 (decoupled from contracts package).

These are the minimal types needed for the recorder. Schemas inline.
"""

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
    levels: dict[str, list[list[float | int]]]
    exchange_ts: str
    repeat: bool = False
    stale: bool = False
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
    ltt: str | None
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
class IngestError:
    """INGEST_ERROR: bad frame/packet logged and skipped."""

    ts: str
    source: str
    reason: str
    offset: int | None
    sha256: str
    raw_b64: str | None = None
