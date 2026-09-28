"""Ask in, bid out. Stated slip when the book is missing."""

from __future__ import annotations

from datetime import datetime

from exitlab.clock import IST, ReplayClock
from exitlab.fills import SlippageModel
from exitlab.types import Bar, Quote


def test_entry_uses_ask_exit_uses_bid() -> None:
    clock = ReplayClock(datetime(2026, 9, 17, 10, 0, tzinfo=IST))
    q = Quote(
        available_ts=datetime(2026, 9, 17, 10, 0, tzinfo=IST),
        bid=149.50,
        ask=150.50,
        ltp=150.00,
        spread=1.0,
    )
    model = SlippageModel()
    assert model.entry_px(q, None, clock) == 150.50
    assert model.exit_px(q, None, clock) == 149.50


def test_missing_book_uses_stated_slip() -> None:
    clock = ReplayClock(datetime(2026, 9, 17, 10, 0, tzinfo=IST))
    bar = Bar(
        ts=datetime(2026, 9, 17, 10, 0, tzinfo=IST),
        available_ts=datetime(2026, 9, 17, 10, 0, tzinfo=IST),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.0,
    )
    model = SlippageModel(slip_frac=0.004)
    assert model.entry_px(None, bar, clock) > 100.0
    assert model.exit_px(None, bar, clock) < 100.0


def test_no_book_uses_half_spread_and_spread_x2_changes() -> None:
    clock = ReplayClock(datetime(2026, 9, 17, 10, 0, tzinfo=IST))
    q = Quote(
        available_ts=datetime(2026, 9, 17, 10, 0, tzinfo=IST),
        bid=None,
        ask=None,
        ltp=100.0,
        spread=0.40,
        strike=23200.0,
        side="CE",
    )
    base = SlippageModel()
    x2 = SlippageModel(spread_mult=2.0)
    buy1, sell1 = base.entry_px(q, None, clock), base.exit_px(q, None, clock)
    buy2, sell2 = x2.entry_px(q, None, clock), x2.exit_px(q, None, clock)
    assert buy1 == 100.20
    assert sell1 == 99.80
    assert buy2 == 100.40
    assert sell2 == 99.60
    assert buy2 > buy1
    assert sell2 < sell1
