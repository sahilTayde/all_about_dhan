"""Tests for deterministic ID generation."""

from datetime import UTC, datetime, timezone

import pytest

from contracts.ids import event_id, order_id, signal_id


def test_order_id_format() -> None:
    """Test order_id format: 27 chars starting with 'aad'."""
    oid = order_id("founder", "sg_test_nifty_20260928_1001_0", "entry")

    assert len(oid) == 27
    assert oid.startswith("aad")
    assert all(c in "abcdef0123456789" or c == "a" for c in oid)  # hex + 'aad' prefix


def test_order_id_deterministic() -> None:
    """Test order_id is deterministic (same inputs -> same output)."""
    oid1 = order_id("founder", "sg_test_nifty_20260928_1001_0", "entry")
    oid2 = order_id("founder", "sg_test_nifty_20260928_1001_0", "entry")
    assert oid1 == oid2


def test_order_id_different_inputs() -> None:
    """Test order_id gives different outputs for different inputs."""
    oid1 = order_id("founder", "sg_test_nifty_20260928_1001_0", "entry")
    oid2 = order_id("founder", "sg_test_nifty_20260928_1001_0", "stop")
    oid3 = order_id("paper", "sg_test_nifty_20260928_1001_0", "entry")

    assert oid1 != oid2  # Different leg
    assert oid1 != oid3  # Different account


def test_order_id_rejects_pipe_in_inputs() -> None:
    """Test order_id rejects inputs containing '|' separator."""
    with pytest.raises(ValueError, match=r"must not contain '\|'"):
        order_id("founder", "sg_test|invalid", "entry")

    with pytest.raises(ValueError, match=r"must not contain '\|'"):
        order_id("founder|invalid", "sg_test", "entry")

    with pytest.raises(ValueError, match=r"must not contain '\|'"):
        order_id("founder", "sg_test", "entry|invalid")


def test_event_id_format() -> None:
    """Test event_id format: 32 char hex string."""
    eid = event_id("engine", "abc123", 0)

    assert len(eid) == 32
    assert all(c in "abcdef0123456789" for c in eid)  # hex chars only


def test_event_id_deterministic() -> None:
    """Test event_id is deterministic."""
    eid1 = event_id("engine", "abc123", 0)
    eid2 = event_id("engine", "abc123", 0)
    assert eid1 == eid2


def test_event_id_different_sequence() -> None:
    """Test event_id changes with sequence number."""
    eid1 = event_id("engine", "abc123", 0)
    eid2 = event_id("engine", "abc123", 1)
    assert eid1 != eid2


def test_signal_id_format() -> None:
    """Test signal_id format matches spec example."""
    from datetime import timedelta

    ist = timezone(timedelta(hours=5, minutes=30))

    dt = datetime(2026, 9, 28, 10, 1, 0, tzinfo=ist)
    sid = signal_id("R8-E1-COIL-SIDE", "1.0.0", "NIFTY", dt, 0)

    # Format: sg_{strategy_slug}_{underlying}_{yyyymmdd}_{hhmm}_{n}
    assert sid.startswith("sg_")
    assert "nifty" in sid
    assert "20260928" in sid
    assert "1001" in sid
    assert sid.endswith("_0")


def test_signal_id_deterministic() -> None:
    """Test signal_id is deterministic."""
    from datetime import timedelta

    ist = timezone(timedelta(hours=5, minutes=30))
    dt = datetime(2026, 9, 28, 10, 1, 0, tzinfo=ist)

    sid1 = signal_id("R8-E1-COIL-SIDE", "1.0.0", "NIFTY", dt, 0)
    sid2 = signal_id("R8-E1-COIL-SIDE", "1.0.0", "NIFTY", dt, 0)
    assert sid1 == sid2


def test_signal_id_rejects_naive_datetime() -> None:
    """Test signal_id rejects naive datetime (no timezone)."""
    naive_dt = datetime(2026, 9, 28, 10, 1, 0)  # No tzinfo

    with pytest.raises(ValueError, match="timezone-aware"):
        signal_id("R8-E1-COIL-SIDE", "1.0.0", "NIFTY", naive_dt, 0)


def test_signal_id_normalizes_to_ist() -> None:
    """Test signal_id normalizes timestamps to IST."""
    from datetime import timedelta

    ist = timezone(timedelta(hours=5, minutes=30))
    utc = UTC

    # Same moment in UTC and IST
    dt_utc = datetime(2026, 9, 28, 4, 31, 0, tzinfo=utc)  # 04:31 UTC
    dt_ist = datetime(2026, 9, 28, 10, 1, 0, tzinfo=ist)  # 10:01 IST (same moment)

    sid_utc = signal_id("R8-E1-COIL-SIDE", "1.0.0", "NIFTY", dt_utc, 0)
    sid_ist = signal_id("R8-E1-COIL-SIDE", "1.0.0", "NIFTY", dt_ist, 0)

    # Should produce same ID (both normalize to IST)
    assert sid_utc == sid_ist
    assert "20260928_1001" in sid_utc  # IST date/time


def test_signal_id_accepts_string_timestamp() -> None:
    """Test signal_id accepts ISO-8601 string timestamp."""
    sid = signal_id("R8-E1-COIL-SIDE", "1.0.0", "NIFTY", "2026-09-28T10:01:00+05:30", 0)

    assert "20260928_1001_0" in sid


def test_signal_id_sequence_numbers() -> None:
    """Test signal_id sequence numbers differentiate signals."""
    from datetime import timedelta

    ist = timezone(timedelta(hours=5, minutes=30))
    dt = datetime(2026, 9, 28, 10, 1, 0, tzinfo=ist)

    sid0 = signal_id("R8-E1", "1.0.0", "NIFTY", dt, 0)
    sid1 = signal_id("R8-E1", "1.0.0", "NIFTY", dt, 1)
    sid2 = signal_id("R8-E1", "1.0.0", "NIFTY", dt, 2)

    assert sid0 != sid1 != sid2
    assert sid0.endswith("_0")
    assert sid1.endswith("_1")
    assert sid2.endswith("_2")


def test_order_id_collision_resistance() -> None:
    """Test order_id collision resistance with many samples."""
    # Generate 1000 order IDs with different inputs
    order_ids = set()
    for account_num in range(10):
        for signal_num in range(10):
            for leg_num in range(10):
                oid = order_id(f"account_{account_num}", f"signal_{signal_num}", f"leg_{leg_num}")
                order_ids.add(oid)

    # All should be unique
    assert len(order_ids) == 1000


def test_signal_id_version_collision_resistance() -> None:
    """Test signal_id distinguishes versions like 1.10.0 vs 11.0.0."""
    from datetime import timedelta

    ist = timezone(timedelta(hours=5, minutes=30))
    dt = datetime(2026, 9, 28, 10, 1, 0, tzinfo=ist)

    # Test version collision resistance
    sid_1_10 = signal_id("R8-E1", "1.10.0", "NIFTY", dt, 0)
    sid_11_0 = signal_id("R8-E1", "11.0.0", "NIFTY", dt, 0)

    # Must be distinct (was bug: both gave sg_r8e1v1100_...)
    assert sid_1_10 != sid_11_0
    assert "v1.10.0" in sid_1_10
    assert "v11.0.0" in sid_11_0


def test_signal_id_strategy_name_collision_resistance() -> None:
    """Test signal_id distinguishes strategy names like R8-E1 vs R8E1."""
    from datetime import timedelta

    ist = timezone(timedelta(hours=5, minutes=30))
    dt = datetime(2026, 9, 28, 10, 1, 0, tzinfo=ist)

    # Test strategy name collision resistance
    sid_with_dash = signal_id("R8-E1", "1.0.0", "NIFTY", dt, 0)
    sid_no_dash = signal_id("R8E1", "1.0.0", "NIFTY", dt, 0)

    # Must be distinct (was bug: both gave sg_r8e1_...)
    assert sid_with_dash != sid_no_dash
    assert "r8-e1" in sid_with_dash
    assert "r8e1" in sid_no_dash
