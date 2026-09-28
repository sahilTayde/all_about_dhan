"""A decision at t must not see data with available_ts > t."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from exitlab.clock import IST, LookAheadError, ReplayClock
from exitlab.harness import assert_no_lookahead, replay_trade
from exitlab.plans import plan_hold_to_1515
from exitlab.types import Bar, Entry, Quote


def _ts(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2026, 9, 17, h, m, s, tzinfo=IST)


def _entry() -> Entry:
    return Entry(
        entry_id="e1",
        ts=_ts(10, 5),
        side="CE",
        strike=23200,
        entry_price=180.0,
        lots=1,
        lot_size=65,
        entry_set="test",
        session="2026-09-17",
        index_at_entry=23300.0,
        moneyness="ITM200",
        scenario="chop",
    )


def test_clock_rejects_future_stamp() -> None:
    clock = ReplayClock(_ts(10, 5))
    with pytest.raises(LookAheadError):
        clock.visible(_ts(10, 6), label="future")


def test_clock_accepts_present_and_past() -> None:
    clock = ReplayClock(_ts(10, 5))
    assert clock.visible(_ts(10, 5), label="now")
    clock.advance_to(_ts(10, 6))
    assert clock.visible(_ts(10, 5, 30), label="past")


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(LookAheadError):
        ReplayClock(datetime(2026, 9, 17, 10, 5))


def test_planted_future_bar_is_invisible() -> None:
    future = Bar(
        ts=_ts(14, 0),
        available_ts=_ts(14, 0),
        open=1.0,
        high=1.0,
        low=1.0,
        close=1.0,
    )
    assert_no_lookahead(_entry(), future, plan_hold_to_1515())


def test_replay_does_not_exit_on_future_crash() -> None:
    """A crash planted after 15:15 must not pull the exit price down at 10:06."""
    entry = _entry()
    good = Quote(available_ts=_ts(10, 6), bid=182.0, ask=183.0, ltp=182.5, index=23310.0)
    crash = Quote(
        available_ts=_ts(15, 20),
        bid=20.0,
        ask=21.0,
        ltp=20.5,
        index=23000.0,
    )
    # Hold-to-15:15 will flatten at 15:15 on the last *visible at that clock* quote.
    # Walk only through 10:06 plus a 15:15 mark, then a later crash.
    flatten = Quote(available_ts=_ts(15, 15), bid=181.0, ask=182.0, ltp=181.5, index=23320.0)
    out = replay_trade(
        entry, plan_hold_to_1515(), quotes=(good, flatten, crash), data_source="synthetic"
    )
    assert out.exit_reason == "FLATTEN_EOD"
    assert out.exit_price is not None
    assert out.exit_price != 20.0
    assert abs(out.exit_price - 181.0) < 1e-9


def test_deliberate_future_read_raises() -> None:
    """Inject a future stamp. The clock must fail (this is the FAIL case)."""
    clock = ReplayClock(_ts(10, 5))
    with pytest.raises(LookAheadError, match="look-ahead"):
        clock.visible(_ts(15, 20), label="injected_future")


def test_1m_bar_not_visible_until_close() -> None:
    clock = ReplayClock(_ts(10, 5, 30))
    bar = Bar(
        ts=_ts(10, 5),
        available_ts=_ts(10, 6),  # close of 10:05 bar
        open=100.0,
        high=110.0,
        low=90.0,
        close=50.0,
    )
    with pytest.raises(LookAheadError):
        clock.visible(bar.available_ts, label="open_bar")
    clock.advance_to(_ts(10, 6))
    assert clock.visible(bar.available_ts, label="closed_bar")
    _ = timedelta
