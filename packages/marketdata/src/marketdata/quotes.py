"""QUOTE_SNAPSHOT every 5 seconds (V2-D2).

Emit bid/ask snapshot for each instrument every 5 seconds.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class QuoteState:
    """Quote state for one instrument."""
    
    last_emit_ts: float
    last_data: dict[str, Any] | None


class QuoteTracker:
    """Track quote snapshots with fixed interval."""
    
    def __init__(self, interval_s: int = 5) -> None:
        """
        Args:
            interval_s: Seconds between snapshots
        """
        self.interval_s = interval_s
        self._state: dict[str, QuoteState] = {}

    def should_emit(self, security_id: str, data: dict[str, Any]) -> bool:
        """
        Check if quote snapshot should be emitted.
        
        Args:
            security_id: Instrument security ID
            data: Quote data from FULL packet
        
        Returns:
            True if should emit snapshot
        """
        now = time.time()
        
        if security_id not in self._state:
            # First packet: emit immediately
            self._state[security_id] = QuoteState(
                last_emit_ts=now,
                last_data=data,
            )
            return True
        
        state = self._state[security_id]
        elapsed_s = now - state.last_emit_ts
        
        if elapsed_s >= self.interval_s:
            state.last_emit_ts = now
            state.last_data = data
            return True
        else:
            # Update data but don't emit yet
            state.last_data = data
            return False

    def get_last_data(self, security_id: str) -> dict[str, Any] | None:
        """Get last data for instrument."""
        state = self._state.get(security_id)
        return state.last_data if state else None
