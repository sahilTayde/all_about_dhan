"""V2-18 pre-market acceptance: available_ts before 09:15; no session-day data."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from premarket.publish import publish

IST = timezone(timedelta(hours=5, minutes=30))
BARS = [
    {"date": "2026-09-24", "open": 100, "high": 102, "low": 99, "close": 101},
    {"date": "2026-09-25", "open": 101, "high": 104, "low": 100, "close": 103},
]


def test_premarket_available_ts_before_0915_and_no_session_day_data(tmp_path: Path) -> None:
    now = datetime(2026, 9, 26, 8, 30, tzinfo=IST)
    env = publish(
        date(2026, 9, 26),
        now=now,
        prior_bars=BARS,
        intermarket={"ES": 5800.0},
        event_days={"2026-09-26": "RBI 11:30"},
        dest=tmp_path / "pm",
    )
    assert env["event_type"] == "PRE_MARKET_SUMMARY"
    assert env["available_ts"] < "2026-09-26T09:15:00+05:30"
    assert env["payload"]["previous_close"] == 103
    assert env["payload"]["holds"] == [{"kind": "EVENT_DAY", "reason": "RBI 11:30"}]
    assert env["payload"]["har_forecast"] is not None
    again = publish(
        date(2026, 9, 26),
        now=now,
        prior_bars=BARS,
        intermarket={"ES": 5800.0},
        event_days={"2026-09-26": "RBI 11:30"},
        dest=tmp_path / "pm",
    )
    assert again["event_id"] == env["event_id"]
    with pytest.raises(ValueError, match="09:15"):
        publish(
            date(2026, 9, 26),
            now=datetime(2026, 9, 26, 9, 15, tzinfo=IST),
            prior_bars=BARS,
            intermarket={},
            event_days={},
            dest=tmp_path / "late",
        )
    with pytest.raises(ValueError, match="session-day"):
        publish(
            date(2026, 9, 26),
            now=now,
            prior_bars=BARS + [{"date": "2026-09-26", "open": 1, "high": 1, "low": 1, "close": 1}],
            intermarket={},
            event_days={},
            dest=tmp_path / "leak",
        )
