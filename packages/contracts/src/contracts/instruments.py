"""Instruments: MarketAdapter protocol and India adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# NSE/BSE equity and F&O trading holidays for 2026
# Source: NSE Circular - Trading Holidays 2026 (Equity & F&O Segment)
# https://www.nseindia.com/companies-listing/corporate-compliance-trading-holidays
# Verified against official NSE circular for 2026
NSE_HOLIDAYS_2026 = {
    date(2026, 1, 15),  # Makar Sankranti
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 3),  # Mahashivratri
    date(2026, 3, 26),  # Holi
    date(2026, 3, 31),  # Id-Ul-Fitr (Ramzan Id)
    date(2026, 4, 3),  # Good Friday
    date(2026, 4, 14),  # Dr. Ambedkar Jayanti
    date(2026, 5, 1),  # Maharashtra Day
    date(2026, 5, 28),  # Buddha Purnima
    date(2026, 6, 26),  # Muharram
    date(2026, 8, 15),  # Independence Day
    date(2026, 8, 27),  # Ganesh Chaturthi
    date(2026, 9, 14),  # Eid-e-Milad
    date(2026, 10, 2),  # Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 10, 27),  # Diwali Laxmi Pujan
    date(2026, 10, 28),  # Diwali Balipratipada
    date(2026, 11, 10),  # Guru Nanak Jayanti
    date(2026, 11, 24),  # Prakash Parv - Guru Nanak Jayanti
    date(2026, 12, 25),  # Christmas
}


@dataclass(frozen=True)
class SessionHours:
    """Market session hours (timezone-aware)."""

    pre_open_start: time
    pre_open_end: time
    market_open: time
    market_close: time
    post_close: time
    timezone: timezone


class MarketAdapter(Protocol):
    """Protocol for market-specific logic."""

    def session_hours(self, session_date: date) -> SessionHours:
        """Return market session hours for given date."""
        ...

    def is_open(self, dt: datetime) -> bool:
        """Check if market is open at given time."""
        ...

    def session_phase(self, dt: datetime) -> str:
        """Return session phase: PRE_OPEN, MARKET, POST_CLOSE, CLOSED."""
        ...

    def is_trading_day(self, d: date) -> bool:
        """Check if date is a trading day (not weekend or holiday)."""
        ...

    def tick_size(self, instrument_id: str) -> float:
        """Return tick size for instrument."""
        ...

    def lot_size(self, symbol: str) -> int:
        """Return lot size for symbol."""
        ...

    def eod_flat_time(self, session_date: date) -> time:
        """Return EOD flatten time (15:15 normally)."""
        ...

    def parse_instrument_id(self, instrument_id: str) -> dict[str, str]:
        """Parse instrument ID into components."""
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

    def __init__(self, holidays: set[date] | None = None) -> None:
        """
        Initialize India adapter.

        Args:
            holidays: Set of holiday dates (uses NSE_HOLIDAYS_2026 by default)
        """
        self._holidays = holidays if holidays is not None else NSE_HOLIDAYS_2026

    def session_hours(self, session_date: date) -> SessionHours:
        """
        Return IST session hours for NSE/BSE.

        Pre-open: 09:00-09:15
        Market: 09:15-15:30
        Post-close: 15:40-16:00 (was 15:30-16:00, spec says 15:40-16:00)
        """
        return SessionHours(
            pre_open_start=time(9, 0, tzinfo=IST),
            pre_open_end=time(9, 15, tzinfo=IST),
            market_open=time(9, 15, tzinfo=IST),
            market_close=time(15, 30, tzinfo=IST),
            post_close=time(16, 0, tzinfo=IST),
            timezone=IST,
        )

    def is_trading_day(self, d: date) -> bool:
        """Check if date is a trading day (not weekend or holiday)."""
        # Monday=0, Sunday=6
        if d.weekday() >= 5:  # Saturday or Sunday
            return False
        return d not in self._holidays

    def is_open(self, dt: datetime) -> bool:
        """Check if market is open at given time."""
        if dt.tzinfo is None:
            raise ValueError("is_open requires timezone-aware datetime")

        dt_ist = dt.astimezone(IST)
        d = dt_ist.date()
        t = dt_ist.time()

        if not self.is_trading_day(d):
            return False

        hours = self.session_hours(d)
        # Replace None tzinfo with IST for comparison
        market_open = hours.market_open.replace(tzinfo=IST)
        market_close = hours.market_close.replace(tzinfo=IST)

        return market_open <= datetime.combine(d, t, tzinfo=IST).timetz() < market_close

    def session_phase(self, dt: datetime) -> str:
        """
        Return session phase.

        Returns: "PRE_OPEN", "MARKET", "POST_CLOSE", or "CLOSED"
        """
        if dt.tzinfo is None:
            raise ValueError("session_phase requires timezone-aware datetime")

        dt_ist = dt.astimezone(IST)
        d = dt_ist.date()
        t = dt_ist.timetz()

        if not self.is_trading_day(d):
            return "CLOSED"

        hours = self.session_hours(d)

        if hours.pre_open_start.replace(tzinfo=IST) <= t < hours.pre_open_end.replace(tzinfo=IST):
            return "PRE_OPEN"
        elif hours.market_open.replace(tzinfo=IST) <= t < hours.market_close.replace(tzinfo=IST):
            return "MARKET"
        elif hours.market_close.replace(tzinfo=IST) <= t < hours.post_close.replace(tzinfo=IST):
            return "POST_CLOSE"
        else:
            return "CLOSED"

    def tick_size(self, instrument_id: str) -> float:
        """
        Return tick size for instrument.

        NSE/BSE F&O: ₹0.05 for options
        """
        # Simple implementation; can be made more sophisticated
        if "FNO" in instrument_id and ("CE" in instrument_id or "PE" in instrument_id):
            return 0.05
        return 0.05

    def lot_size(self, symbol: str) -> int:
        """
        Return lot size for symbol from instrument master.

        Raises:
            ValueError: if symbol is not in instrument master
        """
        lot_sizes = {
            "NIFTY": 65,
            "BANKNIFTY": 30,
            "FINNIFTY": 40,
            "SENSEX": 20,  # Per instrument master
        }
        sym_upper = symbol.upper()
        if sym_upper not in lot_sizes:
            raise ValueError(f"Unknown symbol: {symbol} (not in instrument master)")
        return lot_sizes[sym_upper]

    def eod_flat_time(self, session_date: date) -> time:
        """
        Return EOD flatten time.

        Default: 15:15 IST (V2 architecture section 2.9: EOD flatten on CLOCK after market close).
        The legacy engine uses 15:20 (PR #20 paper_costs.yaml stale_exit_hard_flatten_ist) and
        stays unchanged. V2 uses 15:15 to flatten positions before post-close auction.

        Note: This can be made configurable via engine.yaml if needed; currently returns
        the V2 default from architecture section 2.9 and K16 (REG-15: EOD flatten never
        held back by stale-quote guard).
        """
        return time(15, 15)

    def parse_instrument_id(self, instrument_id: str) -> dict[str, str]:
        """
        Parse instrument ID into components.

        Format examples:
        - Index: NSE_IDX:NIFTY
        - Future: NSE_FNO:NIFTY:2026-09-29
        - Option: NSE_FNO:NIFTY:2026-09-29:24500:CE
        - FX: FX_SPOT:EURUSD

        Returns:
            dict with keys: exchange, segment, symbol, expiry, strike, option_type
            Missing keys have empty string values.

        Raises:
            ValueError: if format is invalid (6+ parts, option_type not CE/PE, expiry without year)
        """
        parts = instrument_id.split(":")
        if len(parts) < 2:
            raise ValueError(f"Invalid instrument_id format: {instrument_id}")

        if len(parts) > 5:
            raise ValueError(f"Invalid instrument_id: too many parts (max 5): {instrument_id}")

        # Parse exchange_segment
        exchange_segment = parts[0]
        if "_" in exchange_segment:
            exchange, segment = exchange_segment.split("_", 1)
        else:
            # Handle FX:EURUSD case
            exchange = exchange_segment
            segment = ""

        symbol = parts[1] if len(parts) > 1 else ""
        expiry = parts[2] if len(parts) > 2 else ""
        strike = parts[3] if len(parts) > 3 else ""
        option_type = parts[4] if len(parts) > 4 else ""

        # Validate expiry (must have 4-digit year if present)
        if expiry and ("-" not in expiry or len(expiry.split("-")[0]) != 4):
            raise ValueError(f"Invalid expiry format (must include year): {expiry}")

        # Validate option_type (must be CE or PE if present)
        if option_type and option_type not in ("CE", "PE"):
            raise ValueError(f"Invalid option_type (must be CE or PE): {option_type}")

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
        - FX: format_instrument_id("FX", "SPOT", "EURUSD") -> "FX_SPOT:EURUSD"
        - Option: format_instrument_id("NSE", "FNO", "NIFTY", "2026-09-29", "24500", "CE")
                  -> "NSE_FNO:NIFTY:2026-09-29:24500:CE"
        """
        # Handle FX case with no segment
        parts = [f"{exchange}_{segment}", symbol] if segment else [exchange, symbol]

        if expiry:
            parts.append(expiry)
        if strike:
            parts.append(strike)
        if option_type:
            parts.append(option_type)
        return ":".join(parts)
