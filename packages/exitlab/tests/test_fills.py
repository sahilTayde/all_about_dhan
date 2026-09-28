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
