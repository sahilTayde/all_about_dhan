"""Health alarms: file + API, optional Telegram. Read-only towards what it watches."""

from health.monitor import STALE_SECONDS, HealthMonitor, in_market_hours, send_telegram

__all__ = ["STALE_SECONDS", "HealthMonitor", "in_market_hours", "send_telegram"]
