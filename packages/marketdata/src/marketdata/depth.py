"""DEPTH_QUOTE throttling and heartbeat (V2-D2).

At most once per second per instrument (throttled to 250ms, 1s heartbeat repeat).
Mark stale: true when depth is older than 5s.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class DepthState:
    """Depth state for one instrument."""
    
    last_emit_ts: float
    last_data_ts: float
    last_data: dict[str, Any]


class DepthTracker:
    """Track depth quotes with throttling and heartbeat."""
    
    def __init__(
        self,
        throttle_ms: int = 250,
        heartbeat_s: int = 1,
        stale_threshold_s: int = 5,
    ) -> None:
        """
        Args:
            throttle_ms: Minimum milliseconds between emits for same instrument
            heartbeat_s: Repeat depth if unchanged after this many seconds
            stale_threshold_s: Mark as stale if older than this
        """
        self.throttle_ms = throttle_ms
        self.heartbeat_s = heartbeat_s
        self.stale_threshold_s = stale_threshold_s
        self._state: dict[str, DepthState] = {}

    def should_emit(self, security_id: str, data: dict[str, Any]) -> tuple[bool, bool]:
        """
        Check if depth should be emitted.
        
        Args:
            security_id: Instrument security ID
            data: Depth data from FULL packet
        
        Returns:
            (should_emit, is_repeat): True if should emit, True if it's a heartbeat repeat
        """
        now = time.time()
        
        if security_id not in self._state:
            # First packet: emit immediately
            self._state[security_id] = DepthState(
                last_emit_ts=now,
                last_data_ts=now,
                last_data=data,
            )
            return (True, False)
        
        state = self._state[security_id]
        
        # Check if data changed
        data_changed = data != state.last_data
        
        if data_changed:
            # Data changed: emit if throttle period passed
            elapsed_ms = (now - state.last_emit_ts) * 1000
            if elapsed_ms >= self.throttle_ms:
                state.last_emit_ts = now
                state.last_data_ts = now
                state.last_data = data
                return (True, False)
            else:
                # Throttled: update data but don't emit yet
                state.last_data_ts = now
                state.last_data = data
                return (False, False)
        else:
            # Data unchanged: emit heartbeat if period passed
            elapsed_s = now - state.last_emit_ts
            if elapsed_s >= self.heartbeat_s:
                state.last_emit_ts = now
                return (True, True)
            else:
                return (False, False)

    def is_stale(self, security_id: str) -> bool:
        """Check if depth is stale (older than threshold)."""
        if security_id not in self._state:
            return False
        
        now = time.time()
        state = self._state[security_id]
        elapsed_s = now - state.last_data_ts
        return elapsed_s > self.stale_threshold_s
