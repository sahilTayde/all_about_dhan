"""Tests for Envelope (V2 event envelope, section 4.4)."""

from contracts.envelope import Envelope


def test_envelope_v2_roundtrip() -> None:
    """Test V2 envelope round-trip through JSON."""
    envelope = Envelope(
        v=2,
        event_type="BAR_CLOSED",
        event_id="5f0c2d6e8a1b4c3d9e7f6a5b4c3d2e1f",
        stream="md:bars:1m",
        source="marketdata",
        event_ts="2026-09-28T10:01:00.000+05:30",
        available_ts="2026-09-28T10:01:01.512+05:30",
        timestamp="2026-09-28T10:01:01.512+05:30",
        account_id=None,
        correlation_id=None,
        causation_id=None,
        payload={"instrument_id": "NSE_IDX:NIFTY", "tf": "1m"},
    )

    # Serialize to JSON
    json_data = envelope.to_json()

    # Check V2 fields are present
    assert json_data["v"] == 2
    assert json_data["event_type"] == "BAR_CLOSED"
    assert json_data["source"] == "marketdata"
    assert json_data["stream"] == "md:bars:1m"
    assert json_data["payload"]["instrument_id"] == "NSE_IDX:NIFTY"

    # Deserialize from JSON
    envelope2 = Envelope.from_json(json_data)
    assert envelope == envelope2


def test_old_event_json_still_loads() -> None:
    """Test that real legacy events.schema.Event JSON still loads (backward compatibility)."""
    from events.schema import Event  # type: ignore[import-untyped]

    # Create a real legacy Event
    legacy_event = Event(
        event_type="POSITION_UPDATE",
        payload={"position_id": "ps_001", "net_qty": 100},
        source="desk",
        event_id="abc123",
        timestamp="2026-09-28T10:01:00.000+05:30",
    )

    # Convert to dict (what from_json receives)
    legacy_dict = {
        "event_type": legacy_event.event_type,
        "payload": legacy_event.payload,
        "source": legacy_event.source,
        "event_id": legacy_event.event_id,
        "timestamp": legacy_event.timestamp,
    }

    # Load via Envelope.from_json (no 'v' field, so it's legacy)
    envelope = Envelope.from_json(legacy_dict)

    # Check fields mapped correctly
    assert envelope.event_type == "POSITION_UPDATE"
    assert envelope.source == "desk"
    assert envelope.event_id == "abc123"
    assert envelope.payload["position_id"] == "ps_001"
    assert envelope.timestamp == "2026-09-28T10:01:00.000+05:30"

    # Check V2-specific fields defaulted from timestamp
    assert envelope.v == 1
    assert envelope.stream == "legacy"
    assert envelope.event_ts == legacy_dict["timestamp"]
    assert envelope.available_ts == legacy_dict["timestamp"]


def test_envelope_spec_example() -> None:
    """Test spec section 4.4 example envelope."""
    # Exact example from section 4.4
    spec_envelope = {
        "v": 2,
        "event_type": "BAR_CLOSED",
        "event_id": "5f0c2d6e8a1b4c3d9e7f6a5b4c3d2e1f",
        "stream": "md:bars:1m",
        "source": "marketdata",
        "event_ts": "2026-09-28T10:01:00.000+05:30",
        "available_ts": "2026-09-28T10:01:01.512+05:30",
        "timestamp": "2026-09-28T10:01:01.512+05:30",
        "account_id": None,
        "correlation_id": None,
        "causation_id": None,
        "payload": {},
    }

    # Load from JSON
    envelope = Envelope.from_json(spec_envelope)
    assert envelope.v == 2
    assert envelope.event_type == "BAR_CLOSED"
    assert envelope.source == "marketdata"
    assert envelope.stream == "md:bars:1m"

    # Round-trip
    assert envelope.to_json() == spec_envelope


def test_envelope_forward_compatibility() -> None:
    """Test forward compatibility: tolerate unknown fields."""
    data = {
        "v": 2,
        "event_type": "SIGNAL",
        "event_id": "sig123",
        "stream": "sig:signals",
        "source": "strategy",
        "event_ts": "2026-09-28T10:01:00+05:30",
        "available_ts": "2026-09-28T10:01:00+05:30",
        "timestamp": "2026-09-28T10:01:00+05:30",
        "account_id": "founder",
        "correlation_id": "bar123",
        "causation_id": "clock456",
        "payload": {"signal_id": "sg_test_nifty_20260928_1001_0"},
        # Unknown future fields (should be tolerated)
        "future_field_1": "value1",
        "future_field_2": {"nested": "data"},
    }

    # Should load without error (forward compatible)
    envelope = Envelope.from_json(data)
    assert envelope.event_type == "SIGNAL"
    assert envelope.account_id == "founder"

    # Output doesn't include unknown fields
    output = envelope.to_json()
    assert "future_field_1" not in output
    assert "future_field_2" not in output
