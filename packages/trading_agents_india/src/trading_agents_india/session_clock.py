"""IST market-hours + founder dead-band clock (MIX-CLOCK-CAS overlay).

Active paper leans: 09:30–15:00 IST.
Session shell: 09:00–15:30 IST (poll may run; dead-band forces HOLD).
Path toward faster ticks: see PLAN_MARKET_HOURS_PAPER_AGENTS.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# NSE cash/F&O shell (VERIFY circular for exact close 15:30 vs 15:40).
SESSION_OPEN = time(9, 0)
SESSION_CLOSE = time(15, 30)

# Founder dead-bands from MIX-CLOCK-CAS: pre-open + CAS window.
DEAD_BAND_MORNING_END = time(9, 30)
DEAD_BAND_AFTERNOON_START = time(15, 0)

# Paper CE/PE emission window (between dead-bands).
ACTIVE_PAPER_START = DEAD_BAND_MORNING_END
ACTIVE_PAPER_END = DEAD_BAND_AFTERNOON_START

# Default poll: 45s (mandate 30–60s). Faster path documented, not default.
DEFAULT_TICK_SECONDS = 45
MIN_TICK_SECONDS = 30
# Documented future floor once chain rate-limits + graph cost allow:
DOCUMENTED_FASTER_TICK_SECONDS = 15


@dataclass(frozen=True)
class ClockSnapshot:
    as_of_ist: datetime
    in_session_shell: bool
    in_dead_band: bool
    allow_directional_paper: bool
    reason: str

    def to_dict(self) -> dict:
        return {
            "as_of_ist": self.as_of_ist.isoformat(timespec="seconds"),
            "in_session_shell": self.in_session_shell,
            "in_dead_band": self.in_dead_band,
            "allow_directional_paper": self.allow_directional_paper,
            "reason": self.reason,
            "overlay": "MIX-CLOCK-CAS",
            "active_paper_window_ist": "09:30–15:00",
            "session_shell_ist": "09:00–15:30",
        }


def now_ist(override: Optional[datetime] = None) -> datetime:
    if override is not None:
        if override.tzinfo is None:
            return override.replace(tzinfo=IST)
        return override.astimezone(IST)
    return datetime.now(IST)


def _t(dt: datetime) -> time:
    return dt.time()


def snapshot(now: Optional[datetime] = None) -> ClockSnapshot:
    dt = now_ist(now)
    # Weekday check — Sat/Sun outside session shell
    if dt.weekday() >= 5:
        return ClockSnapshot(
            as_of_ist=dt,
            in_session_shell=False,
            in_dead_band=False,
            allow_directional_paper=False,
            reason="weekend: outside NSE session shell",
        )
    t = _t(dt)
    in_shell = SESSION_OPEN <= t < SESSION_CLOSE
    if not in_shell:
        return ClockSnapshot(
            as_of_ist=dt,
            in_session_shell=False,
            in_dead_band=False,
            allow_directional_paper=False,
            reason="outside session shell 09:00–15:30 IST",
        )
    in_dead = t < DEAD_BAND_MORNING_END or t >= DEAD_BAND_AFTERNOON_START
    if in_dead:
        return ClockSnapshot(
            as_of_ist=dt,
            in_session_shell=True,
            in_dead_band=True,
            allow_directional_paper=False,
            reason="MIX-CLOCK-CAS dead-band (09:00–09:30 or 15:00–15:30) → HOLD only",
        )
    return ClockSnapshot(
        as_of_ist=dt,
        in_session_shell=True,
        in_dead_band=False,
        allow_directional_paper=True,
        reason="active paper window 09:30–15:00 IST",
    )


def clamp_tick_seconds(raw: int) -> int:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_TICK_SECONDS
    if n < MIN_TICK_SECONDS:
        return MIN_TICK_SECONDS
    if n > 300:
        return 300
    return n


def next_tick_deadline(tick_seconds: int, now: Optional[datetime] = None) -> datetime:
    dt = now_ist(now)
    return dt + timedelta(seconds=clamp_tick_seconds(tick_seconds))


# UTC fallback helper for environments without zoneinfo data (rare).
def utc_offset_ist() -> timezone:
    return timezone(timedelta(hours=5, minutes=30))
