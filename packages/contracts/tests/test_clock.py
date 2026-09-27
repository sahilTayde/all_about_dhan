"""Tests for Clock (SimClock, LiveClock)."""

from datetime import UTC, datetime, timedelta

import pytest

from contracts.clock import IST, LiveClock, SimClock


def test_liveclock_returns_ist() -> None:
    """Test that LiveClock returns IST timezone."""
    clock = LiveClock()
    now = clock.now()
    assert now.tzinfo == IST
    assert now.utcoffset() == timedelta(hours=5, minutes=30)


def test_simclock_initialization() -> None:
    """Test SimClock initialization."""
    start = datetime(2026, 9, 28, 9, 15, 0, tzinfo=IST)
    clock = SimClock(start)
    assert clock.now() == start


def test_simclock_rejects_naive_start() -> None:
    """Test that SimClock rejects naive datetime (no timezone)."""
    naive_dt = datetime(2026, 9, 28, 9, 15, 0)  # No tzinfo
    with pytest.raises(ValueError, match="timezone-aware"):
        SimClock(naive_dt)


def test_simclock_advance_to() -> None:
    """Test SimClock.advance_to moves clock forward."""
    start = datetime(2026, 9, 28, 9, 15, 0, tzinfo=IST)
    clock = SimClock(start)

    # Advance 1 hour
    new_time = datetime(2026, 9, 28, 10, 15, 0, tzinfo=IST)
    clock.advance_to(new_time)
    assert clock.now() == new_time

    # Advance 5 minutes
    new_time2 = datetime(2026, 9, 28, 10, 20, 0, tzinfo=IST)
    clock.advance_to(new_time2)
    assert clock.now() == new_time2


def test_simclock_advance_to_refuses_backwards() -> None:
    """Test that SimClock.advance_to raises when going backwards."""
    start = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    clock = SimClock(start)

    # Try to go back 1 hour
    past_time = datetime(2026, 9, 28, 9, 0, 0, tzinfo=IST)
    with pytest.raises(ValueError, match="cannot go backwards"):
        clock.advance_to(past_time)

    # Clock should remain at start
    assert clock.now() == start


def test_simclock_advance_to_rejects_naive() -> None:
    """Test that SimClock.advance_to rejects naive datetime."""
    start = datetime(2026, 9, 28, 9, 15, 0, tzinfo=IST)
    clock = SimClock(start)

    naive_dt = datetime(2026, 9, 28, 10, 0, 0)  # No tzinfo
    with pytest.raises(ValueError, match="timezone-aware"):
        clock.advance_to(naive_dt)


def test_simclock_advance_by() -> None:
    """Test SimClock.advance_by with positive delta."""
    start = datetime(2026, 9, 28, 9, 15, 0, tzinfo=IST)
    clock = SimClock(start)

    # Advance by 1 hour
    clock.advance_by(timedelta(hours=1))
    assert clock.now() == datetime(2026, 9, 28, 10, 15, 0, tzinfo=IST)

    # Advance by 30 seconds
    clock.advance_by(timedelta(seconds=30))
    assert clock.now() == datetime(2026, 9, 28, 10, 15, 30, tzinfo=IST)


def test_simclock_advance_by_refuses_negative() -> None:
    """Test that SimClock.advance_by refuses negative delta."""
    start = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    clock = SimClock(start)

    # Try to go back
    with pytest.raises(ValueError, match="negative delta"):
        clock.advance_by(timedelta(hours=-1))

    # Clock should remain at start
    assert clock.now() == start


def test_simclock_advance_by_zero_is_ok() -> None:
    """Test that SimClock.advance_by accepts zero delta."""
    start = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    clock = SimClock(start)

    # Zero delta should be allowed (no change)
    clock.advance_by(timedelta(0))
    assert clock.now() == start


def test_simclock_cross_timezone() -> None:
    """Test SimClock with different timezones."""
    # Start in UTC
    utc = UTC
    start_utc = datetime(2026, 9, 28, 4, 0, 0, tzinfo=utc)
    clock = SimClock(start_utc)

    # Advance to IST time
    new_ist = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    clock.advance_to(new_ist)

    # Clock should be at the new time
    assert clock.now() == new_ist
    # Convert to UTC to verify equivalence (10:00 IST = 04:30 UTC)
    assert clock.now().astimezone(utc) == datetime(2026, 9, 28, 4, 30, 0, tzinfo=utc)
