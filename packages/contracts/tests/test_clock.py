"""Tests for clock.py - SimClock and LiveClock."""

from datetime import datetime, timedelta

import pytest

from contracts.clock import IST, LiveClock, SimClock


def test_live_clock_returns_current_time() -> None:
    """LiveClock.now() returns current wall time in IST."""
    clock = LiveClock()
    now1 = clock.now()
    now2 = clock.now()
    assert now1.tzinfo == IST
    assert now2.tzinfo == IST
    assert now2 >= now1


def test_sim_clock_starts_at_given_time() -> None:
    """SimClock starts at the given time."""
    start = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    clock = SimClock(start)
    assert clock.now() == start


def test_sim_clock_advance_to() -> None:
    """SimClock.advance_to() moves time forward."""
    start = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    clock = SimClock(start)
    new_time = datetime(2026, 9, 28, 10, 1, 0, tzinfo=IST)
    clock.advance_to(new_time)
    assert clock.now() == new_time


def test_sim_clock_advance_to_raises_on_backwards() -> None:
    """SimClock.advance_to raises when going backwards (acceptance criterion)."""
    start = datetime(2026, 9, 28, 10, 1, 0, tzinfo=IST)
    clock = SimClock(start)
    past = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    
    with pytest.raises(ValueError, match="cannot go backwards"):
        clock.advance_to(past)


def test_sim_clock_advance_by() -> None:
    """SimClock.advance_by() adds delta."""
    start = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    clock = SimClock(start)
    clock.advance_by(timedelta(minutes=5))
    expected = datetime(2026, 9, 28, 10, 5, 0, tzinfo=IST)
    assert clock.now() == expected


def test_sim_clock_requires_timezone_aware_start() -> None:
    """SimClock raises if start is naive (no timezone)."""
    naive_dt = datetime(2026, 9, 28, 10, 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        SimClock(naive_dt)


def test_sim_clock_advance_to_requires_timezone_aware() -> None:
    """SimClock.advance_to raises if new_time is naive."""
    start = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    clock = SimClock(start)
    naive_dt = datetime(2026, 9, 28, 10, 1, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        clock.advance_to(naive_dt)


def test_sim_clock_advance_to_same_time_is_ok() -> None:
    """SimClock.advance_to with same time does not raise."""
    start = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    clock = SimClock(start)
    clock.advance_to(start)  # Same time is OK
    assert clock.now() == start
