"""Instruments: MarketAdapter protocol and India adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Protocol


@dataclass(frozen=True)
class SessionHours:
    """Market session hours."""

    pre_open_start: time
    pre_open_end: time
    market_open: time
    market_close: time
    post_close: time


class MarketAdapter(Protocol):
    """Protocol for market-specific logic (calendar, hours, lot size, tick size, margins)."""

    @property
    def session_hours(self) -> SessionHours:
        """Return market session hours."""
        ...

    def parse_instrument_id(self, instrument_id: str) -> dict[str, str]:
        """
        Parse instrument ID into components.

        Returns dict with keys: exchange, segment, symbol, expiry, strike, option_type
        """
        ...

    def format_instrument_id(
        self,
        exchange: str,
        segment: str,
        symbol: str,
        expiry: str | None = None,
        strike: str | None = None,
        option_type: str | None = None,
    ) -> str:
        """Format components into instrument ID string."""
        ...


class India:
    """India market adapter (NSE/BSE)."""

    @property
    def session_hours(self) -> SessionHours:
        """
        Return IST session hours for NSE/BSE.

        Pre-open: 09:00-09:15
        Market: 09:15-15:30
        Post-close: 15:30-16:00 (for auction)
        """
        return SessionHours(
            pre_open_start=time(9, 0),
            pre_open_end=time(9, 15),
            market_open=time(9, 15),
            market_close=time(15, 30),
            post_close=time(16, 0),
        )

    def parse_instrument_id(self, instrument_id: str) -> dict[str, str]:
        """
        Parse instrument ID into components.

        Format examples:
        - Index: NSE_IDX:NIFTY
        - Future: NSE_FNO:NIFTY:2026-09-29
        - Option: NSE_FNO:NIFTY:2026-09-29:24500:CE
        - BSE: BSE_FNO:SENSEX:2026-10-01:81000:PE

        Returns:
            dict with keys: exchange, segment, symbol, expiry, strike, option_type
            Missing keys have empty string values.
        """
        parts = instrument_id.split(":")
        if len(parts) < 2:
            raise ValueError(f"Invalid instrument_id format: {instrument_id}")

        exchange_segment = parts[0]
        exchange, segment = exchange_segment.split("_", 1) if "_" in exchange_segment else (parts[0], "")
        symbol = parts[1] if len(parts) > 1 else ""
        expiry = parts[2] if len(parts) > 2 else ""
        strike = parts[3] if len(parts) > 3 else ""
        option_type = parts[4] if len(parts) > 4 else ""

        return {
            "exchange": exchange,
            "segment": segment,
            "symbol": symbol,
            "expiry": expiry,
            "strike": strike,
            "option_type": option_type,
        }

    def format_instrument_id(
        self,
        exchange: str,
        segment: str,
        symbol: str,
        expiry: str | None = None,
        strike: str | None = None,
        option_type: str | None = None,
    ) -> str:
        """
        Format components into instrument ID string.

        Examples:
        - Index: format_instrument_id("NSE", "IDX", "NIFTY") -> "NSE_IDX:NIFTY"
        - Option: format_instrument_id("NSE", "FNO", "NIFTY", "2026-09-29", "24500", "CE")
                  -> "NSE_FNO:NIFTY:2026-09-29:24500:CE"
        """
        parts = [f"{exchange}_{segment}", symbol]
        if expiry:
            parts.append(expiry)
        if strike:
            parts.append(strike)
        if option_type:
            parts.append(option_type)
        return ":".join(parts)
