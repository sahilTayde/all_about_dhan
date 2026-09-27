"""Tests for MarketAdapter and India adapter."""

from datetime import date, datetime, time

import pytest

from contracts.instruments import IST, NSE_HOLIDAYS_2026, India


def test_india_session_hours() -> None:
    """Test India session hours (NSE/BSE)."""
    india = India()
    hours = india.session_hours(date(2026, 9, 28))

    assert hours.pre_open_start == time(9, 0, tzinfo=IST)
    assert hours.pre_open_end == time(9, 15, tzinfo=IST)
    assert hours.market_open == time(9, 15, tzinfo=IST)
    assert hours.market_close == time(15, 30, tzinfo=IST)
    assert hours.post_close == time(16, 0, tzinfo=IST)
    assert hours.timezone == IST


def test_india_is_trading_day_weekdays() -> None:
    """Test is_trading_day returns True for weekdays (not holidays)."""
    india = India()

    # Monday-Friday in a week without holidays
    monday = date(2026, 9, 21)
    assert monday.weekday() == 0  # Monday
    assert india.is_trading_day(monday)

    friday = date(2026, 9, 25)
    assert friday.weekday() == 4  # Friday
    assert india.is_trading_day(friday)


def test_india_is_trading_day_weekends() -> None:
    """Test is_trading_day returns False for weekends."""
    india = India()

    # Saturday and Sunday
    saturday = date(2026, 9, 26)
    assert saturday.weekday() == 5
    assert not india.is_trading_day(saturday)

    sunday = date(2026, 9, 27)
    assert sunday.weekday() == 6
    assert not india.is_trading_day(sunday)


def test_india_is_trading_day_holidays() -> None:
    """Test is_trading_day returns False for NSE holidays."""
    india = India()

    # Republic Day (Monday, but holiday)
    republic_day = date(2026, 1, 26)
    assert republic_day in NSE_HOLIDAYS_2026
    assert not india.is_trading_day(republic_day)

    # Diwali
    diwali = date(2026, 10, 27)
    assert diwali in NSE_HOLIDAYS_2026
    assert not india.is_trading_day(diwali)


def test_india_is_open_during_market_hours() -> None:
    """Test is_open returns True during market hours (09:15-15:30)."""
    india = India()

    # Trading day at 10:00 IST (during market hours)
    dt = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    assert india.is_open(dt)

    # Trading day at 15:00 IST (still open)
    dt = datetime(2026, 9, 28, 15, 0, 0, tzinfo=IST)
    assert india.is_open(dt)


def test_india_is_open_outside_market_hours() -> None:
    """Test is_open returns False outside market hours."""
    india = India()

    # Before market open (09:00 IST)
    dt = datetime(2026, 9, 28, 9, 0, 0, tzinfo=IST)
    assert not india.is_open(dt)

    # After market close (15:31 IST)
    dt = datetime(2026, 9, 28, 15, 31, 0, tzinfo=IST)
    assert not india.is_open(dt)


def test_india_is_open_on_holiday() -> None:
    """Test is_open returns False on holidays."""
    india = India()

    # Republic Day at 10:00 IST (normally open, but holiday)
    dt = datetime(2026, 1, 26, 10, 0, 0, tzinfo=IST)
    assert not india.is_open(dt)


def test_india_is_open_rejects_naive_datetime() -> None:
    """Test is_open raises on naive datetime."""
    india = India()
    naive_dt = datetime(2026, 9, 28, 10, 0, 0)  # No tzinfo

    with pytest.raises(ValueError, match="timezone-aware"):
        india.is_open(naive_dt)


def test_india_session_phase_pre_open() -> None:
    """Test session_phase returns PRE_OPEN during pre-open (09:00-09:15)."""
    india = India()

    dt = datetime(2026, 9, 28, 9, 10, 0, tzinfo=IST)
    assert india.session_phase(dt) == "PRE_OPEN"


def test_india_session_phase_market() -> None:
    """Test session_phase returns MARKET during market hours (09:15-15:30)."""
    india = India()

    dt = datetime(2026, 9, 28, 10, 0, 0, tzinfo=IST)
    assert india.session_phase(dt) == "MARKET"

    dt = datetime(2026, 9, 28, 15, 15, 0, tzinfo=IST)
    assert india.session_phase(dt) == "MARKET"


def test_india_session_phase_post_close() -> None:
    """Test session_phase returns POST_CLOSE after market close (15:30-16:00)."""
    india = India()

    dt = datetime(2026, 9, 28, 15, 45, 0, tzinfo=IST)
    assert india.session_phase(dt) == "POST_CLOSE"


def test_india_session_phase_closed() -> None:
    """Test session_phase returns CLOSED outside session hours or on holidays."""
    india = India()

    # Before pre-open
    dt = datetime(2026, 9, 28, 8, 0, 0, tzinfo=IST)
    assert india.session_phase(dt) == "CLOSED"

    # After post-close
    dt = datetime(2026, 9, 28, 17, 0, 0, tzinfo=IST)
    assert india.session_phase(dt) == "CLOSED"

    # Weekend
    dt = datetime(2026, 9, 27, 10, 0, 0, tzinfo=IST)  # Sunday
    assert india.session_phase(dt) == "CLOSED"

    # Holiday
    dt = datetime(2026, 1, 26, 10, 0, 0, tzinfo=IST)  # Republic Day
    assert india.session_phase(dt) == "CLOSED"


def test_india_session_phase_rejects_naive_datetime() -> None:
    """Test session_phase raises on naive datetime."""
    india = India()
    naive_dt = datetime(2026, 9, 28, 10, 0, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        india.session_phase(naive_dt)


def test_india_eod_flat_time() -> None:
    """Test EOD flatten time is 15:15 (V2 spec section 2.9)."""
    india = India()
    flat_time = india.eod_flat_time(date(2026, 9, 28))

    assert flat_time == time(15, 15)


def test_india_tick_size() -> None:
    """Test tick size for NSE F&O options (₹0.05)."""
    india = India()

    # Option
    tick = india.tick_size("NSE_FNO:NIFTY:2026-09-29:24500:CE")
    assert tick == 0.05


def test_india_lot_size() -> None:
    """Test lot sizes for major indices (from instrument master)."""
    india = India()

    assert india.lot_size("NIFTY") == 65
    assert india.lot_size("BANKNIFTY") == 30
    assert india.lot_size("FINNIFTY") == 40
    assert india.lot_size("SENSEX") == 20  # Per instrument master


def test_india_parse_instrument_id_index() -> None:
    """Test parse_instrument_id for index."""
    india = India()
    parsed = india.parse_instrument_id("NSE_IDX:NIFTY")

    assert parsed["exchange"] == "NSE"
    assert parsed["segment"] == "IDX"
    assert parsed["symbol"] == "NIFTY"
    assert parsed["expiry"] == ""
    assert parsed["strike"] == ""
    assert parsed["option_type"] == ""


def test_india_parse_instrument_id_option() -> None:
    """Test parse_instrument_id for option."""
    india = India()
    parsed = india.parse_instrument_id("NSE_FNO:NIFTY:2026-09-29:24500:CE")

    assert parsed["exchange"] == "NSE"
    assert parsed["segment"] == "FNO"
    assert parsed["symbol"] == "NIFTY"
    assert parsed["expiry"] == "2026-09-29"
    assert parsed["strike"] == "24500"
    assert parsed["option_type"] == "CE"


def test_india_parse_instrument_id_rejects_invalid_option_type() -> None:
    """Test parse_instrument_id rejects invalid option type."""
    india = India()

    with pytest.raises(ValueError, match="must be CE or PE"):
        india.parse_instrument_id("NSE_FNO:NIFTY:2026-09-29:24500:XX")


def test_india_parse_instrument_id_rejects_expiry_without_year() -> None:
    """Test parse_instrument_id rejects expiry without year."""
    india = India()

    with pytest.raises(ValueError, match="must include year"):
        india.parse_instrument_id("NSE_FNO:NIFTY:09-29:24500:CE")


def test_india_parse_instrument_id_rejects_too_many_parts() -> None:
    """Test parse_instrument_id rejects 6+ part IDs."""
    india = India()

    with pytest.raises(ValueError, match="too many parts"):
        india.parse_instrument_id("NSE_FNO:NIFTY:2026-09-29:24500:CE:EXTRA")


def test_india_format_instrument_id_index() -> None:
    """Test format_instrument_id for index."""
    india = India()
    instrument_id = india.format_instrument_id("NSE", "IDX", "NIFTY")

    assert instrument_id == "NSE_IDX:NIFTY"


def test_india_format_instrument_id_option() -> None:
    """Test format_instrument_id for option."""
    india = India()
    instrument_id = india.format_instrument_id("NSE", "FNO", "NIFTY", "2026-09-29", "24500", "CE")

    assert instrument_id == "NSE_FNO:NIFTY:2026-09-29:24500:CE"


def test_india_format_instrument_id_fx() -> None:
    """Test format_instrument_id for FX (no segment)."""
    india = India()
    instrument_id = india.format_instrument_id("FX", "SPOT", "EURUSD")

    assert instrument_id == "FX_SPOT:EURUSD"


def test_india_custom_holidays() -> None:
    """Test India adapter accepts custom holiday set."""
    custom_holidays = {date(2026, 12, 31)}  # New Year's Eve (normally not a holiday)
    india = India(holidays=custom_holidays)

    # Regular NSE holiday (Republic Day) should now be a trading day
    assert india.is_trading_day(date(2026, 1, 26))

    # Custom holiday (New Year's Eve) should not be a trading day
    assert not india.is_trading_day(date(2026, 12, 31))


def test_nse_holidays_2026_count() -> None:
    """Test NSE 2026 holidays set has expected count (per official NSE circular)."""
    # NSE 2026 has 20 trading holidays per official circular
    assert len(NSE_HOLIDAYS_2026) == 20


def test_nse_holidays_2026_includes_major_holidays() -> None:
    """Test NSE 2026 holidays includes major holidays."""
    # Major holidays that must be present
    assert date(2026, 1, 26) in NSE_HOLIDAYS_2026  # Republic Day
    assert date(2026, 8, 15) in NSE_HOLIDAYS_2026  # Independence Day
    assert date(2026, 10, 2) in NSE_HOLIDAYS_2026  # Gandhi Jayanti
    assert date(2026, 12, 25) in NSE_HOLIDAYS_2026  # Christmas
