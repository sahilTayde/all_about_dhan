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

# Cash F&O open 09:15 IST. First NEW paper ticket only after +35m.
CASH_OPEN = time(9, 15)
OPEN_SETTLE_MINUTES = 35
NEW_PAPER_START = time(9, 50)  # 09:15 + 35m
NO_NEW_BEFORE_0950 = "NO_NEW_BEFORE_0950"
OPEN_SETTLE_35M = "OPEN_SETTLE_35M"

# Paper CE/PE emission window (after open-settle; before afternoon dead-band).
ACTIVE_PAPER_START = NEW_PAPER_START
ACTIVE_PAPER_END = DEAD_BAND_AFTERNOON_START

# Live mock: 10s REST dual-tape. WS stays off (no greeks on feed parse).
DEFAULT_TICK_SECONDS = 10
MIN_TICK_SECONDS = 10
DOCUMENTED_FASTER_TICK_SECONDS = 10


@dataclass(frozen=True)
class ClockSnapshot:
    as_of_ist: datetime
    in_session_shell: bool
    in_dead_band: bool
    allow_directional_paper: bool
    reason: str
    allow_flatten_cancel: bool = False
    allow_new_paper_ticket: bool = False
    open_settle_gate: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "as_of_ist": self.as_of_ist.isoformat(timespec="seconds"),
            "in_session_shell": self.in_session_shell,
            "in_dead_band": self.in_dead_band,
            "allow_directional_paper": self.allow_directional_paper,
            "allow_flatten_cancel": self.allow_flatten_cancel,
            "allow_new_paper_ticket": self.allow_new_paper_ticket,
            "open_settle_gate": self.open_settle_gate,
            "reason": self.reason,
            "overlay": "MIX-CLOCK-CAS + OPEN_SETTLE_35M",
            "active_paper_window_ist": "09:50–15:00",
            "session_shell_ist": "09:00–15:30",
            "cash_open_ist": "09:15",
            "no_new_before_ist": "09:50",
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
            allow_flatten_cancel=False,
            allow_new_paper_ticket=False,
            reason="outside session shell 09:00–15:30 IST",
        )
    cas_dead = t < DEAD_BAND_MORNING_END or t >= DEAD_BAND_AFTERNOON_START
    settle_hold = t < NEW_PAPER_START
    allow_new = (not settle_hold) and t < DEAD_BAND_AFTERNOON_START
    if settle_hold:
        gate = OPEN_SETTLE_35M if t >= CASH_OPEN else NO_NEW_BEFORE_0950
        return ClockSnapshot(
            as_of_ist=dt,
            in_session_shell=True,
            in_dead_band=True,
            allow_directional_paper=False,
            allow_flatten_cancel=True,
            allow_new_paper_ticket=False,
            open_settle_gate=gate,
            reason=(
                f"{gate}: cash open 09:15 + {OPEN_SETTLE_MINUTES}m → first NEW paper at 09:50 IST. "
                "Flatten/cancel of already-open still allowed."
            ),
        )
    if cas_dead:
        return ClockSnapshot(
            as_of_ist=dt,
            in_session_shell=True,
            in_dead_band=True,
            allow_directional_paper=False,
            allow_flatten_cancel=True,
            allow_new_paper_ticket=False,
            reason="MIX-CLOCK-CAS dead-band (15:00–15:30) → HOLD new; flatten/cancel still allowed",
        )
    return ClockSnapshot(
        as_of_ist=dt,
        in_session_shell=True,
        in_dead_band=False,
        allow_directional_paper=True,
        allow_flatten_cancel=True,
        allow_new_paper_ticket=True,
        reason="active paper window 09:50–15:00 IST",
    )


def new_paper_gate(now: Optional[datetime] = None) -> dict:
    """Named 09:50 IST gate for NEW paper tickets. Flatten is separate."""
    snap = snapshot(now)
    return {
        "allow": bool(snap.allow_new_paper_ticket),
        "gate": snap.open_settle_gate or ("OK" if snap.allow_new_paper_ticket else snap.reason),
        "flatten_ok": bool(snap.allow_flatten_cancel),
        "reason": snap.reason,
        "named": NO_NEW_BEFORE_0950 if not snap.allow_new_paper_ticket and snap.in_session_shell else None,
    }


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
