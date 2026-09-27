"""Tests for MarketAdapter and India adapter."""

from datetime import date, datetime, time

import pytest

from contracts.instruments import IST, NSE_HOLIDAY_LABELS_2026, NSE_HOLIDAYS_2026, India


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

    # Dussehra
    dussehra = date(2026, 10, 20)
    assert dussehra in NSE_HOLIDAYS_2026
    assert not india.is_trading_day(dussehra)


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
    """NSE 2026 weekday holiday set is 17 dates."""
    assert len(NSE_HOLIDAYS_2026) == 17
    assert set(NSE_HOLIDAY_LABELS_2026) == NSE_HOLIDAYS_2026


def test_nse_holidays_2026_pins_every_date_and_label() -> None:
    """Pin every 2026 holiday date and its exchange label."""
    expected = {
        date(2026, 1, 15): "municipal election",
        date(2026, 1, 26): "Republic Day",
        date(2026, 3, 3): "Holi",
        date(2026, 3, 26): "Ram Navami",
        date(2026, 3, 31): "Mahavir Jayanti",
        date(2026, 4, 3): "Good Friday",
        date(2026, 4, 14): "Dr. Ambedkar Jayanti",
        date(2026, 5, 1): "Maharashtra Day",
        date(2026, 5, 28): "Bakri Id",
        date(2026, 6, 26): "Muharram",
        date(2026, 8, 15): "Independence Day",
        date(2026, 9, 14): "Ganesh Chaturthi",
        date(2026, 10, 2): "Gandhi Jayanti",
        date(2026, 10, 20): "Dussehra",
        date(2026, 11, 10): "Diwali-Balipratipada",
        date(2026, 11, 24): "Guru Nanak Dev",
        date(2026, 12, 25): "Christmas",
    }
    assert expected == NSE_HOLIDAY_LABELS_2026
    india = India()
    for day in expected:
        assert not india.is_trading_day(day)


def test_nse_2026_selected_weekdays_are_trading_days() -> None:
    """Aug 27, Oct 27, Oct 28 2026 are weekdays and not holidays."""
    india = India()
    for day in (date(2026, 8, 27), date(2026, 10, 27), date(2026, 10, 28)):
        assert day.weekday() < 5
        assert day not in NSE_HOLIDAYS_2026
        assert india.is_trading_day(day)


def test_india_is_trading_day_full_year_consistency() -> None:
    """Test is_trading_day consistency over full year 2026."""
    from datetime import timedelta

    india = India()

    # Iterate through every day of 2026
    start_date = date(2026, 1, 1)
    end_date = date(2026, 12, 31)
    current = start_date

    trading_days = 0
    non_trading_days = 0

    while current <= end_date:
        is_weekend = current.weekday() in (5, 6)  # Saturday or Sunday
        is_holiday = current in NSE_HOLIDAYS_2026

        if is_weekend or is_holiday:
            # Should not be a trading day
            assert not india.is_trading_day(current), f"{current} should not be a trading day"
            non_trading_days += 1
        else:
            # Should be a trading day (weekday, not holiday)
            assert india.is_trading_day(current), f"{current} should be a trading day"
            trading_days += 1

        current += timedelta(days=1)

    # Sanity check: 2026 has 365 days
    assert trading_days + non_trading_days == 365
    # 2026 has 52 weeks + 1 day (starts on Thursday), so 104 weekend days
    # Plus 17 holidays (some may fall on weekends, but NSE_HOLIDAYS_2026 only lists weekday
    # holidays). So expect approximately 365 - 104 - 17 = 244 trading days
    assert 240 <= trading_days <= 250, f"Expected ~244 trading days, got {trading_days}"
