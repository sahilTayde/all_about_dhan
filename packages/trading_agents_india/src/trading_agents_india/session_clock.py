"""IST cash-hours clock. Founder lock — no exception until founder says.

India has **no** Sat/Sun cash/F&O session. Dual-tape must not run on weekends.
Mon–Fri only:
  - Work / NEW paper: 09:30 IST inclusive until 15:16 IST exclusive
  - Flatten every OPEN book at 15:16:00 IST
  - Capture ticks (no NEW, no open books) until 15:29:00 IST exclusive
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# Founder lock 2026-09-19. Do not widen without founder ask.
PAPER_WORK_START = time(9, 30)
PAPER_FLAT = time(15, 16)
TICK_CAPTURE_END = time(15, 29)
CASH_OPEN = time(9, 15)

# Compat names (old 09:50 / 15:15 clock retired).
SESSION_OPEN = PAPER_WORK_START
SESSION_CLOSE = TICK_CAPTURE_END
DEAD_BAND_MORNING_END = PAPER_WORK_START
DEAD_BAND_AFTERNOON_START = PAPER_FLAT
PAPER_STOP = PAPER_FLAT
NEW_PAPER_START = PAPER_WORK_START
OPEN_SETTLE_MINUTES = 15  # 09:15 cash open → 09:30 first NEW
NO_NEW_BEFORE_0930 = "NO_NEW_BEFORE_0930"
NO_NEW_BEFORE_0950 = NO_NEW_BEFORE_0930  # alias
OPEN_SETTLE_35M = NO_NEW_BEFORE_0930  # alias — 35m settle retired
WEEKEND_NO_MARKET = "WEEKEND_NO_MARKET"
NO_NEW_AFTER_1516 = "NO_NEW_AFTER_1516"
NO_NEW_AFTER_1515 = NO_NEW_AFTER_1516  # alias
FLATTEN_1516 = "FLATTEN_1516"
BEFORE_WORK_START = "BEFORE_0930_IST"
PAST_TICK_CAPTURE = "PAST_1529_IST"

# FOUNDER LOCK: Dhan dual-tape + board write default. Do not raise until founder names another interval.
DEFAULT_TICK_SECONDS = 2
MIN_TICK_SECONDS = 2
DOCUMENTED_FASTER_TICK_SECONDS = 2


@dataclass(frozen=True)
class ClockSnapshot:
    as_of_ist: datetime
    in_session_shell: bool
    in_dead_band: bool
    allow_directional_paper: bool
    reason: str
    allow_flatten_cancel: bool = False
    allow_new_paper_ticket: bool = False
    allow_tick_capture: bool = False
    open_settle_gate: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "as_of_ist": self.as_of_ist.isoformat(timespec="seconds"),
            "in_session_shell": self.in_session_shell,
            "in_dead_band": self.in_dead_band,
            "allow_directional_paper": self.allow_directional_paper,
            "allow_flatten_cancel": self.allow_flatten_cancel,
            "allow_new_paper_ticket": self.allow_new_paper_ticket,
            "allow_tick_capture": self.allow_tick_capture,
            "open_settle_gate": self.open_settle_gate,
            "reason": self.reason,
            "overlay": "FOUNDER_LOCK Mon–Fri 09:30–15:16 NEW; flatten 15:16; ticks to 15:29; no Sat/Sun",
            "active_paper_window_ist": "09:30–15:16",
            "tick_capture_ist": "09:30–15:29",
            "flatten_ist": "15:16",
            "session_shell_ist": "09:30–15:29 Mon–Fri",
            "cash_open_ist": "09:15",
            "no_new_before_ist": "09:30",
            "weekday_only": True,
        }


def now_ist(override: Optional[datetime] = None) -> datetime:
    if override is not None:
        if override.tzinfo is None:
            return override.replace(tzinfo=IST)
        return override.astimezone(IST)
    return datetime.now(IST)


def _t(dt: datetime) -> time:
    return now_ist(dt).time()


def is_nse_weekday(now: Optional[datetime] = None) -> bool:
    """Mon–Fri IST. Sat/Sun are not Indian cash/F&O days."""
    return now_ist(now).weekday() < 5


def allow_tick_capture(now: Optional[datetime] = None) -> bool:
    dt = now_ist(now)
    if dt.weekday() >= 5:
        return False
    t = _t(dt)
    return PAPER_WORK_START <= t < TICK_CAPTURE_END


def allow_new_paper(now: Optional[datetime] = None) -> bool:
    dt = now_ist(now)
    if dt.weekday() >= 5:
        return False
    t = _t(dt)
    return PAPER_WORK_START <= t < PAPER_FLAT


def must_flatten_books(now: Optional[datetime] = None) -> bool:
    """True at/after 15:16 IST on a weekday, or any time on Sat/Sun leftovers."""
    dt = now_ist(now)
    if dt.weekday() >= 5:
        return True
    return _t(dt) >= PAPER_FLAT


def dual_tape_live_gate(now: Optional[datetime] = None) -> tuple[bool, str]:
    """Live dual-tape may run only Mon–Fri 09:30 ≤ t < 15:29 IST. No weekend. No exception."""
    dt = now_ist(now)
    if dt.weekday() >= 5:
        return False, WEEKEND_NO_MARKET
    t = _t(dt)
    if t < PAPER_WORK_START:
        return False, BEFORE_WORK_START
    if t >= TICK_CAPTURE_END:
        return False, PAST_TICK_CAPTURE
    return True, "OK"


def snapshot(now: Optional[datetime] = None, *, expiry_day: bool = False) -> ClockSnapshot:
    del expiry_day  # founder lock: CAS does not override Mon–Fri 09:30–15:16
    dt = now_ist(now)
    if dt.weekday() >= 5:
        return ClockSnapshot(
            as_of_ist=dt,
            in_session_shell=False,
            in_dead_band=False,
            allow_directional_paper=False,
            allow_flatten_cancel=True,
            allow_new_paper_ticket=False,
            allow_tick_capture=False,
            open_settle_gate=WEEKEND_NO_MARKET,
            reason="WEEKEND_NO_MARKET: no Sat/Sun India cash/F&O. Dual-tape must not run.",
        )
    t = _t(dt)
    if t < PAPER_WORK_START:
        return ClockSnapshot(
            as_of_ist=dt,
            in_session_shell=False,
            in_dead_band=True,
            allow_directional_paper=False,
            allow_flatten_cancel=True,
            allow_new_paper_ticket=False,
            allow_tick_capture=False,
            open_settle_gate=NO_NEW_BEFORE_0930,
            reason="NO_NEW_BEFORE_0930: work starts 09:30 IST Mon–Fri only. Flatten leftover still allowed.",
        )
    if t >= TICK_CAPTURE_END:
        return ClockSnapshot(
            as_of_ist=dt,
            in_session_shell=False,
            in_dead_band=False,
            allow_directional_paper=False,
            allow_flatten_cancel=True,
            allow_new_paper_ticket=False,
            allow_tick_capture=False,
            reason="PAST_1529_IST: tick capture ends 15:29 IST. Books already flattened at 15:16.",
        )
    capture_only = t >= PAPER_FLAT
    return ClockSnapshot(
        as_of_ist=dt,
        in_session_shell=True,
        in_dead_band=capture_only,
        allow_directional_paper=not capture_only,
        allow_flatten_cancel=True,
        allow_new_paper_ticket=not capture_only,
        allow_tick_capture=True,
        open_settle_gate=NO_NEW_AFTER_1516 if capture_only else None,
        reason=(
            "NO_NEW_AFTER_1516: flatten all books at 15:16 IST; ticks only until 15:29."
            if capture_only
            else "active paper window 09:30–15:16 IST Mon–Fri"
        ),
    )


def new_paper_gate(now: Optional[datetime] = None) -> dict:
    snap = snapshot(now)
    return {
        "allow": bool(snap.allow_new_paper_ticket),
        "gate": snap.open_settle_gate or ("OK" if snap.allow_new_paper_ticket else snap.reason),
        "flatten_ok": bool(snap.allow_flatten_cancel),
        "reason": snap.reason,
        "named": snap.open_settle_gate if not snap.allow_new_paper_ticket else None,
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


def utc_offset_ist() -> timezone:
    return timezone(timedelta(hours=5, minutes=30))
