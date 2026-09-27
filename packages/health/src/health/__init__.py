"""Health alarms: file + API, optional Telegram. Read-only towards what it watches.

V2-14 adds snapshot checks, a loopback /metrics endpoint, and queued alert sinks
that must not stall the event bus. Existing HealthMonitor is unchanged.
"""

from health.monitor import STALE_SECONDS, HealthMonitor, in_market_hours, send_telegram

__all__ = ["STALE_SECONDS", "HealthMonitor", "in_market_hours", "send_telegram"]
