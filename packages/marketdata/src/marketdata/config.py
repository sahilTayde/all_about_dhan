"""Configuration for market data recorder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecorderConfig:
    """Market data recorder configuration."""

    tape_root: Path
    underlying: str = "NIFTY"
    depth_throttle_ms: int = 250
    depth_heartbeat_s: int = 1
    quote_snapshot_interval_s: int = 5
    oi_cadence_window_s: int = 60
    stale_depth_threshold_s: int = 5
    old_strike_retention_s: int = 600
    publish_to_bus: bool = False
