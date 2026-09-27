"""Tests for instruments.py - MarketAdapter and India adapter."""

from datetime import time

from contracts.instruments import India


def test_india_session_hours() -> None:
    """India adapter has correct session hours."""
    india = India()
    hours = india.session_hours
    
    assert hours.pre_open_start == time(9, 0)
    assert hours.pre_open_end == time(9, 15)
    assert hours.market_open == time(9, 15)
    assert hours.market_close == time(15, 30)
    assert hours.post_close == time(16, 0)


def test_india_parse_index() -> None:
    """India.parse_instrument_id parses index format."""
    india = India()
    parsed = india.parse_instrument_id("NSE_IDX:NIFTY")
    assert parsed["exchange"] == "NSE"
    assert parsed["segment"] == "IDX"
    assert parsed["symbol"] == "NIFTY"
    assert parsed["expiry"] == ""
    assert parsed["strike"] == ""
    assert parsed["option_type"] == ""


def test_india_parse_option() -> None:
    """India.parse_instrument_id parses option format."""
    india = India()
    parsed = india.parse_instrument_id("NSE_FNO:NIFTY:2026-09-29:24500:CE")
    assert parsed["exchange"] == "NSE"
    assert parsed["segment"] == "FNO"
    assert parsed["symbol"] == "NIFTY"
    assert parsed["expiry"] == "2026-09-29"
    assert parsed["strike"] == "24500"
    assert parsed["option_type"] == "CE"


def test_india_parse_bse_option() -> None:
    """India.parse_instrument_id parses BSE option."""
    india = India()
    parsed = india.parse_instrument_id("BSE_FNO:SENSEX:2026-10-01:81000:PE")
    assert parsed["exchange"] == "BSE"
    assert parsed["segment"] == "FNO"
    assert parsed["symbol"] == "SENSEX"
    assert parsed["expiry"] == "2026-10-01"
    assert parsed["strike"] == "81000"
    assert parsed["option_type"] == "PE"


def test_india_format_index() -> None:
    """India.format_instrument_id formats index."""
    india = India()
    iid = india.format_instrument_id("NSE", "IDX", "NIFTY")
    assert iid == "NSE_IDX:NIFTY"


def test_india_format_option() -> None:
    """India.format_instrument_id formats option."""
    india = India()
    iid = india.format_instrument_id("NSE", "FNO", "NIFTY", "2026-09-29", "24500", "CE")
    assert iid == "NSE_FNO:NIFTY:2026-09-29:24500:CE"


def test_india_format_future() -> None:
    """India.format_instrument_id formats future."""
    india = India()
    iid = india.format_instrument_id("NSE", "FNO", "NIFTY", "2026-09-29")
    assert iid == "NSE_FNO:NIFTY:2026-09-29"


def test_india_round_trip() -> None:
    """India parse and format are inverses."""
    india = India()
    original = "NSE_FNO:BANKNIFTY:2026-09-28:52000:PE"
    parsed = india.parse_instrument_id(original)
    formatted = india.format_instrument_id(
        parsed["exchange"],
        parsed["segment"],
        parsed["symbol"],
        parsed["expiry"],
        parsed["strike"],
        parsed["option_type"],
    )
    assert formatted == original
