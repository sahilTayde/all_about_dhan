"""Configuration for market data recorder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecorderConfig:
    """Market data recorder configuration."""
    
    tape_root: Path
    """Root directory for tape files (e.g. data/tape/v2 or tmp_path/tape/v2 for tests)"""
    
    underlying: str = "NIFTY"
    """Underlying to track (NIFTY, BANKNIFTY, SENSEX)"""
    
    depth_throttle_ms: int = 250
    """Minimum milliseconds between DEPTH_QUOTE for same instrument"""
    
    depth_heartbeat_s: int = 1
    """Seconds to repeat DEPTH_QUOTE if unchanged"""
    
    quote_snapshot_interval_s: int = 5
    """Seconds between QUOTE_SNAPSHOT"""
    
    oi_cadence_window_s: int = 60
    """Window in seconds for OI cadence measurement"""
    
    stale_depth_threshold_s: int = 5
    """Mark depth as stale if older than this many seconds"""
    
    old_strike_retention_s: int = 600
    """Keep unsubscribed strikes for this many seconds (10 minutes)"""
    
    publish_to_bus: bool = False
    """Publish events to Redis bus (off by default)"""
