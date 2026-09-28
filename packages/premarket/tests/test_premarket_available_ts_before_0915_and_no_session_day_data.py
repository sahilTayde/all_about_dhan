"""V2-18 pre-market acceptance: available_ts before 09:15; no session-day data."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from warehouse.calendar import NonTradingDay, trading_date_from_now

from premarket.publish import main, publish

IST = timezone(timedelta(hours=5, minutes=30))
BARS = [
    {"date": "2026-09-23", "open": 100, "high": 102, "low": 99, "close": 101},
    {"date": "2026-09-24", "open": 101, "high": 104, "low": 100, "close": 103},
]


def test_premarket_available_ts_before_0915_and_no_session_day_data(tmp_path: Path) -> None:
    now = datetime(2026, 9, 25, 8, 30, tzinfo=IST)
    env = publish(
        date(2026, 9, 25),
        now=now,
        prior_bars=BARS,
        intermarket={"ES": 5800.0},
        event_days={"2026-09-25": "RBI 11:30"},
        dest=tmp_path / "pm",
    )
    assert env["event_type"] == "PRE_MARKET_SUMMARY"
    assert env["available_ts"] < "2026-09-25T09:15:00+05:30"
    assert env["payload"]["previous_close"] == 103
    assert env["payload"]["holds"] == [{"kind": "EVENT_DAY", "reason": "RBI 11:30"}]
    assert env["payload"]["har_forecast"] is not None
    again = publish(
        date(2026, 9, 25),
        now=now,
        prior_bars=BARS,
        intermarket={"ES": 5800.0},
        event_days={"2026-09-25": "RBI 11:30"},
        dest=tmp_path / "pm",
    )
    assert again["event_id"] == env["event_id"]
    with pytest.raises(ValueError, match="09:15"):
        publish(
            date(2026, 9, 25),
            now=datetime(2026, 9, 25, 9, 15, tzinfo=IST),
            prior_bars=BARS,
            intermarket={},
            event_days={},
            dest=tmp_path / "late",
        )
    with pytest.raises(ValueError, match="session-day"):
        publish(
            date(2026, 9, 25),
            now=now,
            prior_bars=BARS + [{"date": "2026-09-25", "open": 1, "high": 1, "low": 1, "close": 1}],
            intermarket={},
            event_days={},
            dest=tmp_path / "leak",
        )


def test_sunday_and_2026_10_02_refused(tmp_path: Path) -> None:
    now_sun = datetime(2026, 9, 27, 8, 0, tzinfo=IST)
    now_holiday = datetime(2026, 10, 2, 8, 0, tzinfo=IST)
    with pytest.raises(NonTradingDay):
        publish(date(2026, 9, 27), now=now_sun, prior_bars=BARS, intermarket={}, event_days={}, dest=tmp_path / "sun")
    with pytest.raises(NonTradingDay):
        publish(
            date(2026, 10, 2), now=now_holiday, prior_bars=BARS, intermarket={}, event_days={}, dest=tmp_path / "gandhi"
        )
    assert not (tmp_path / "sun").exists()
    assert not (tmp_path / "gandhi").exists()
    prior = tmp_path / "bars.json"
    prior.write_text("[]", encoding="utf-8")
    assert (
        main(
            [
                "--session",
                "2026-09-27",
                "--now",
                now_sun.isoformat(),
                "--prior",
                str(prior),
                "--out",
                str(tmp_path / "cli-sun"),
            ]
        )
        == 2
    )
    assert not (tmp_path / "cli-sun").exists()


def test_ct_evening_maps_to_ist_date(tmp_path: Path) -> None:
    now = datetime(2026, 9, 24, 19, 0, tzinfo=ZoneInfo("America/Chicago"))
    assert trading_date_from_now(now).isoformat() == "2026-09-25"
    env = publish(None, now=now, prior_bars=BARS, intermarket={}, event_days={}, dest=tmp_path / "pm")
    assert env["payload"]["session"] == "2026-09-25"
    assert (tmp_path / "pm" / "PRE_MARKET_SUMMARY.2026-09-25.json").is_file()
