"""Recorder configuration. Defaults are the V2-D2 spec values."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecorderConfig:
    tape_root: Path
    underlying: str = "NIFTY"
    # Resolved instruments are cached here; used if Dhan is unreachable at startup.
    cache_dir: Path | None = None
    startup_attempts: int = 5
    # Network failures at startup are retried until max(09:20 IST, now + 2 min).
    startup_retry_s: float = 30.0
    depth_throttle_s: float = 0.25
    # Heartbeat after 0.9 s of silence, checked every tick_s, keeps row gaps <= ~1.0 s.
    depth_heartbeat_s: float = 0.9
    tick_s: float = 0.1
    quote_interval_s: int = 5
    oi_window_s: int = 60
    stale_after_s: float = 5.0
    retention_s: float = 600.0
    max_instruments: int = 100
    connect_early_s: float = 120.0
    # Re-centre from the option-chain spot when no index tick arrived for this long.
    spot_fallback_after_s: float = 20.0
    spot_poll_s: float = 30.0
    max_backoff_s: float = 30.0
    # Consecutive websocket handshakes rejected with HTTP 401/403 before giving up.
    max_auth_failures: int = 3
