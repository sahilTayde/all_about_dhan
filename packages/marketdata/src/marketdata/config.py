"""Recorder configuration. Defaults are the V2-D2 spec values."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecorderConfig:
    tape_root: Path
    # Single-name field kept for existing constructors. Prefer ``underlyings``.
    underlying: str = "NIFTY"
    # Empty means ``(underlying,)``. The CLI default is NIFTY,SENSEX.
    underlyings: tuple[str, ...] = ()
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
    # Re-centre from the option-chain spot only while no index tick has arrived.
    # After the first index tick, the chain is never used for spot.
    spot_fallback_after_s: float = 20.0
    # Shared account budget with the legacy desk: at most one fallback / 60 s.
    spot_poll_s: float = 60.0
    max_backoff_s: float = 30.0
    # Consecutive websocket handshakes rejected with HTTP 401/403 before giving up.
    max_auth_failures: int = 3
    # Background tape flusher: short put-timeout, then drop. close() waits the queue out.
    tape_queue_max: int = 256
    tape_queue_put_timeout_s: float = 0.05
    # IDX_I: ticker (15) or quote (17). FULL (21) sends no index ticks on the live feed.
    index_feed_mode: str = "ticker"

    def resolved_underlyings(self) -> tuple[str, ...]:
        """Names the recorder loads. Tests that omit ``underlyings`` stay NIFTY-only."""
        return self.underlyings if self.underlyings else (self.underlying,)
