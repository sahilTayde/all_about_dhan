"""OI_CADENCE tracking: how often OI actually changes per instrument (V2-D2).

Emit every minute: count, median and max gap between OI changes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class OiState:
    """OI state for one instrument."""
    
    last_oi: int | None = None
    last_change_ts: float | None = None
    change_timestamps: list[float] = field(default_factory=list)
    window_start_ts: float = field(default_factory=time.time)


class OiCadenceTracker:
    """Track OI update frequency."""
    
    def __init__(self, window_s: int = 60) -> None:
        """
        Args:
            window_s: Window in seconds for cadence measurement
        """
        self.window_s = window_s
        self._state: dict[str, OiState] = {}

    def update(self, security_id: str, oi: int) -> None:
        """Update OI value for instrument."""
        now = time.time()
        
        if security_id not in self._state:
            self._state[security_id] = OiState(
                last_oi=oi,
                last_change_ts=now,
                change_timestamps=[now],
                window_start_ts=now,
            )
            return
        
        state = self._state[security_id]
        
        # Check if OI changed
        if oi != state.last_oi:
            state.last_oi = oi
            state.last_change_ts = now
            state.change_timestamps.append(now)

    def should_emit(self, security_id: str) -> bool:
        """Check if cadence stats should be emitted."""
        if security_id not in self._state:
            return False
        
        now = time.time()
        state = self._state[security_id]
        elapsed_s = now - state.window_start_ts
        
        return elapsed_s >= self.window_s

    def compute_stats(self, security_id: str) -> dict[str, any]:
        """
        Compute cadence stats for instrument.
        
        Returns:
            Dict with keys: oi_updates (count), median_gap_s, p90_gap_s
        """
        if security_id not in self._state:
            return {
                "oi_updates": 0,
                "median_gap_s": None,
                "p90_gap_s": None,
            }
        
        state = self._state[security_id]
        timestamps = state.change_timestamps
        
        if len(timestamps) < 2:
            return {
                "oi_updates": len(timestamps),
                "median_gap_s": None,
                "p90_gap_s": None,
            }
        
        # Compute gaps between consecutive changes
        gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps) - 1)]
        gaps.sort()
        
        # Median
        mid = len(gaps) // 2
        median_gap = gaps[mid] if len(gaps) % 2 == 1 else (gaps[mid-1] + gaps[mid]) / 2
        
        # P90
        p90_idx = int(len(gaps) * 0.9)
        p90_gap = gaps[min(p90_idx, len(gaps) - 1)]
        
        return {
            "oi_updates": len(timestamps),
            "median_gap_s": round(median_gap, 2),
            "p90_gap_s": round(p90_gap, 2),
        }

    def reset_window(self, security_id: str) -> None:
        """Reset window for next measurement period."""
        if security_id not in self._state:
            return
        
        state = self._state[security_id]
        state.window_start_ts = time.time()
        state.change_timestamps = []
