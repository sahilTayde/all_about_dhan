"""Session clocks from STRAT-007 / STRAT-009. Asia/Kolkata. No edge claim."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def minutes_ist(ts: int) -> int:
    dt = datetime.fromtimestamp(int(ts), tz=IST)
    return dt.hour * 60 + dt.minute


def skip_open_009(ts: int) -> bool:
    """STRAT-009: ignore 09:15–09:45 IST."""
    m = minutes_ist(ts)
    return 9 * 60 + 15 <= m < 9 * 60 + 45


def flatten_009(ts: int) -> bool:
    """STRAT-009: flatten before 15:15 IST."""
    return minutes_ist(ts) >= 15 * 60 + 15


def in_founder_dead_band(ts: int) -> bool:
    """Founder freeze: no tape 09:00–09:30 or 15:00–15:30 IST (pre-open + CAS)."""
    m = minutes_ist(ts)
    return (9 * 60 <= m <= 9 * 60 + 30) or (15 * 60 <= m <= 15 * 60 + 30)


def drop_dead_band(bars: list) -> list:
    return [b for b in bars if not in_founder_dead_band(b.ts)]


def allow_007(ts: int) -> bool:
    """STRAT-007: new entries 10:00–14:30 IST."""
    m = minutes_ist(ts)
    return 10 * 60 <= m < 14 * 60 + 30


def session_date_ist(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=IST).date().isoformat()
