"""Tests for payloads.py - round-trip dataclass to JSON to schema validation."""

import json
from dataclasses import asdict

import pytest

from contracts.payloads import (
    CatastrophicStop,
    DepthQuote,
    Level,
    OiCadence,
    QuoteSnapshot,
    StrikeChoice,
    StrikeQuote,
    TimeStop,
)


def test_depth_quote_round_trip() -> None:
    """DEPTH_QUOTE round-trips dataclass -> JSON -> schema validation (acceptance criterion)."""
    dq = DepthQuote(
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        bid=151.10,
        bid_qty=1950,
        ask=151.35,
        ask_qty=1300,
        ltp=151.20,
        oi=4412350,
        levels={
            "bid": [[151.10, 1950], [151.05, 2600]],
            "ask": [[151.35, 1300], [151.40, 2275]],
        },
        exchange_ts="2026-09-28T10:01:01.230+05:30",
        repeat=False,
        raw_b64=None,
    )
    
    # Dataclass to dict
    payload = asdict(dq)
    
    # Dict to JSON
    json_str = json.dumps(payload)
    
    # JSON back to dict
    parsed = json.loads(json_str)
    
    # Validate against schema
    try:
        from contracts.validation import validate
        validate(parsed, "depth_quote")
    except ImportError:
        pytest.skip("jsonschema not installed")
    
    # Round-trip
    assert parsed["instrument_id"] == dq.instrument_id
    assert parsed["bid"] == dq.bid


def test_quote_snapshot_round_trip() -> None:
    """QUOTE_SNAPSHOT round-trips (acceptance criterion)."""
    qs = QuoteSnapshot(
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        rule="ITM100",
        side="CE",
        bid=151.10,
        ask=151.35,
        mid=151.225,
        spread=0.25,
        ltp=151.20,
        ltt="2026-09-28T10:01:04.910+05:30",
        oi=4412350,
        depth_age_ms=310,
        stale=False,
    )
    
    payload = asdict(qs)
    json_str = json.dumps(payload)
    parsed = json.loads(json_str)
    
    try:
        from contracts.validation import validate
        validate(parsed, "quote_snapshot")
    except ImportError:
        pytest.skip("jsonschema not installed")
    
    assert parsed["instrument_id"] == qs.instrument_id
    assert parsed["rule"] == "ITM100"


def test_oi_cadence_round_trip() -> None:
    """OI_CADENCE round-trips (acceptance criterion)."""
    oi = OiCadence(
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        window_s=60,
        oi_updates=2,
        median_gap_s=31.0,
        p90_gap_s=58.0,
        last_oi_change="2026-09-28T10:00:47.100+05:30",
        sources=["feed_oi", "full", "chain"],
    )
    
    payload = asdict(oi)
    json_str = json.dumps(payload)
    parsed = json.loads(json_str)
    
    try:
        from contracts.validation import validate
        validate(parsed, "oi_cadence")
    except ImportError:
        pytest.skip("jsonschema not installed")
    
    assert parsed["instrument_id"] == oi.instrument_id
    assert parsed["oi_updates"] == 2


def test_time_stop_round_trip() -> None:
    """TimeStop round-trips (acceptance criterion)."""
    ts = TimeStop(after_s=180, when="entry_in:09:15-10:00", unless_profit_pts=5.0)
    
    payload = asdict(ts)
    json_str = json.dumps(payload)
    parsed = json.loads(json_str)
    
    try:
        from contracts.validation import validate
        validate(parsed, "time_stop")
    except ImportError:
        pytest.skip("jsonschema not installed")
    
    assert parsed["after_s"] == 180
    assert parsed["when"] == "entry_in:09:15-10:00"


def test_strike_choice_round_trip() -> None:
    """StrikeChoice round-trips (acceptance criterion)."""
    sq1 = StrikeQuote(
        rule="ATM",
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24500:CE",
        bid=88.05,
        ask=88.25,
        mid=88.15,
        spread=0.20,
        quote_age_ms=640,
        est_delta=0.51,
        est_round_trip_pts=0.64,
    )
    sq2 = StrikeQuote(
        rule="ITM100",
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        bid=151.10,
        ask=151.35,
        mid=151.23,
        spread=0.25,
        quote_age_ms=410,
        est_delta=0.66,
        est_round_trip_pts=0.88,
    )
    
    sc = StrikeChoice(
        chosen="ITM100",
        reason="LOWEST_BREAKEVEN_AT_HOLD",
        rule_version="router-1.0.0+9c2e",
        alternatives=(sq1, sq2),
    )
    
    # Convert nested dataclasses
    payload = {
        "chosen": sc.chosen,
        "reason": sc.reason,
        "rule_version": sc.rule_version,
        "alternatives": [asdict(alt) for alt in sc.alternatives],
    }
    
    json_str = json.dumps(payload)
    parsed = json.loads(json_str)
    
    try:
        from contracts.validation import validate
        validate(parsed, "strike_choice")
    except ImportError:
        pytest.skip("jsonschema not installed")
    
    assert parsed["chosen"] == "ITM100"
    assert len(parsed["alternatives"]) == 2
