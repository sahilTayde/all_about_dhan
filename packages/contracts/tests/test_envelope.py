"""Tests for envelope.py - V2 envelope compatible with events.schema.Event."""

import json

import pytest

from contracts.envelope import Envelope
from events.schema import Event


def test_envelope_has_required_fields() -> None:
    """Envelope has all required fields."""
    env = Envelope(event_type="TEST", payload={"x": 1}, source="test")
    assert env.event_type == "TEST"
    assert env.payload == {"x": 1}
    assert env.source == "test"
    assert env.event_id  # Auto-generated
    assert env.timestamp  # Auto-generated
    assert env.v == 2


def test_envelope_has_v2_fields() -> None:
    """Envelope has new V2 fields."""
    env = Envelope(
        event_type="BAR_CLOSED",
        payload={},
        stream="md:bars:1m",
        event_ts="2026-09-28T10:01:00.000+05:30",
        available_ts="2026-09-28T10:01:01.512+05:30",
    )
    assert env.v == 2
    assert env.stream == "md:bars:1m"
    assert env.event_ts == "2026-09-28T10:01:00.000+05:30"
    assert env.available_ts == "2026-09-28T10:01:01.512+05:30"


def test_envelope_to_json_round_trip() -> None:
    """Envelope serializes to JSON and back."""
    env = Envelope(
        event_type="SIGNAL",
        payload={"signal_id": "sg_test_001", "side": "CE"},
        source="strategy",
        stream="sig:signals",
    )
    json_str = env.to_json()
    env2 = Envelope.from_json(json_str)
    assert env2.event_type == env.event_type
    assert env2.payload == env.payload
    assert env2.source == env.source
    assert env2.stream == env.stream
    assert env2.v == 2


def test_old_event_json_still_loads() -> None:
    """An old Event JSON (v1 or no v) loads as Envelope."""
    # Create an old-format event using the existing Event class
    old_event = Event(event_type="MARKET_TICK", payload={"ltp": 24512.35}, source="feed")
    old_json = old_event.to_json()
    
    # Should load as Envelope
    env = Envelope.from_json(old_json)
    assert env.event_type == "MARKET_TICK"
    assert env.payload == {"ltp": 24512.35}
    assert env.source == "feed"
    # V2 fields are None for old format
    assert env.stream is None
    assert env.event_ts is None


def test_envelope_json_is_valid_json() -> None:
    """Envelope JSON is parseable."""
    env = Envelope(event_type="TEST", payload={"x": 1.5}, source="test")
    json_str = env.to_json()
    parsed = json.loads(json_str)
    assert parsed["event_type"] == "TEST"
    assert parsed["payload"]["x"] == 1.5
    assert parsed["v"] == 2


def test_envelope_forbids_nan_in_payload() -> None:
    """Envelope.to_json raises on NaN values."""
    env = Envelope(event_type="TEST", payload={"x": float("nan")}, source="test")
    with pytest.raises(ValueError):
        env.to_json()
