"""Strike set management for traded instruments (V2-D2).

Tracks ATM, ITM100, ITM200 on CE/PE for nearest weekly expiry, plus index and future.
Re-centers on spot moves. Keeps old strikes for 10 minutes. Always keeps open positions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from dhan_client.types import FeedInstrument


@dataclass(frozen=True)
class StrikeInfo:
    """Information about a subscribed strike."""
    
    instrument: FeedInstrument
    rule: str  # "ATM" | "ITM100" | "ITM200" | "INDEX" | "FUTURE"
    side: str  # "CE" | "PE" | "INDEX" | "FUTURE"
    strike: int | None
    subscribed_at: float
    last_seen_at: float


class StrikeSetManager:
    """Manage traded strike set with re-centering and retention."""
    
    def __init__(
        self,
        underlying: str,
        retention_seconds: int = 600,
        get_open_position_strikes: Callable[[], set[int]] | None = None,
    ) -> None:
        """
        Args:
            underlying: Underlying symbol (NIFTY, BANKNIFTY, SENSEX)
            retention_seconds: Keep old strikes for this many seconds (default 10 minutes)
            get_open_position_strikes: Hook to get strikes with open positions (always kept)
        """
        self.underlying = underlying
        self.retention_seconds = retention_seconds
        self.get_open_position_strikes = get_open_position_strikes or (lambda: set())
        
        self._current_strikes: dict[str, StrikeInfo] = {}
        self._last_spot: float | None = None
        self._last_recenter: float = 0.0

    def update_spot(self, spot: float) -> list[FeedInstrument]:
        """
        Update spot price and re-center if needed.
        
        Returns:
            List of new instruments to subscribe (empty if no re-center needed)
        """
        now = time.time()
        self._last_spot = spot
        
        # Re-center if spot moved significantly (placeholder: always re-center first time)
        if self._last_recenter == 0.0 or self._should_recenter(spot):
            self._last_recenter = now
            new_strikes = self._compute_strike_set(spot)
            
            # Add new strikes to current set
            to_subscribe = []
            for strike_info in new_strikes:
                key = self._strike_key(strike_info)
                if key not in self._current_strikes:
                    self._current_strikes[key] = strike_info
                    to_subscribe.append(strike_info.instrument)
                else:
                    # Update last_seen_at for existing strikes
                    self._current_strikes[key] = strike_info
            
            return to_subscribe
        
        return []

    def _should_recenter(self, spot: float) -> bool:
        """Check if spot moved enough to trigger re-centering."""
        # ponytail: simple rule for now (re-center if moved > 50 points)
        if self._last_spot is None:
            return True
        return abs(spot - self._last_spot) > 50.0

    def _compute_strike_set(self, spot: float) -> list[StrikeInfo]:
        """Compute strike set for current spot."""
        now = time.time()
        strikes = []
        
        # Round spot to nearest 50 for strike calculation
        atm_strike = round(spot / 50) * 50
        itm100_strike = atm_strike + 100
        itm200_strike = atm_strike + 200
        
        # CE strikes (calls)
        for rule, strike in [("ATM", atm_strike), ("ITM100", itm100_strike), ("ITM200", itm200_strike)]:
            strikes.append(
                StrikeInfo(
                    instrument=FeedInstrument(
                        exchange_segment=f"NSE_FNO" if self.underlying != "SENSEX" else "BSE_FNO",
                        security_id=f"{self.underlying}_CE_{strike}",  # placeholder
                    ),
                    rule=rule,
                    side="CE",
                    strike=strike,
                    subscribed_at=now,
                    last_seen_at=now,
                )
            )
        
        # PE strikes (puts)
        for rule, strike in [("ATM", atm_strike), ("ITM100", atm_strike - 100), ("ITM200", atm_strike - 200)]:
            strikes.append(
                StrikeInfo(
                    instrument=FeedInstrument(
                        exchange_segment=f"NSE_FNO" if self.underlying != "SENSEX" else "BSE_FNO",
                        security_id=f"{self.underlying}_PE_{strike}",  # placeholder
                    ),
                    rule=rule,
                    side="PE",
                    strike=strike,
                    subscribed_at=now,
                    last_seen_at=now,
                )
            )
        
        # Add index and future (placeholder security IDs)
        strikes.append(
            StrikeInfo(
                instrument=FeedInstrument(
                    exchange_segment="NSE_IDX" if self.underlying != "SENSEX" else "BSE_IDX",
                    security_id=f"{self.underlying}_INDEX",
                ),
                rule="INDEX",
                side="INDEX",
                strike=None,
                subscribed_at=now,
                last_seen_at=now,
            )
        )
        strikes.append(
            StrikeInfo(
                instrument=FeedInstrument(
                    exchange_segment="NSE_FNO" if self.underlying != "SENSEX" else "BSE_FNO",
                    security_id=f"{self.underlying}_FUT",
                ),
                rule="FUTURE",
                side="FUTURE",
                strike=None,
                subscribed_at=now,
                last_seen_at=now,
            )
        )
        
        return strikes

    def _strike_key(self, info: StrikeInfo) -> str:
        """Generate unique key for strike."""
        return f"{info.instrument.exchange_segment}:{info.instrument.security_id}"

    def cleanup_old_strikes(self) -> list[FeedInstrument]:
        """
        Remove strikes that are older than retention period and not in open positions.
        
        Returns:
            List of instruments to unsubscribe
        """
        now = time.time()
        open_strikes = self.get_open_position_strikes()
        to_remove = []
        
        for key, info in list(self._current_strikes.items()):
            # Keep if still within retention period
            if now - info.last_seen_at < self.retention_seconds:
                continue
            
            # Keep if has open position
            if info.strike is not None and info.strike in open_strikes:
                continue
            
            # Remove
            to_remove.append(info.instrument)
            del self._current_strikes[key]
        
        return to_remove

    def get_current_instruments(self) -> list[FeedInstrument]:
        """Get all currently subscribed instruments."""
        return [info.instrument for info in self._current_strikes.values()]

    def get_strike_rule(self, security_id: str) -> tuple[str, str] | None:
        """Get (rule, side) for a security_id, or None if not tracked."""
        for info in self._current_strikes.values():
            if info.instrument.security_id == security_id:
                return (info.rule, info.side)
        return None
