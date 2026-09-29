"""R3 fill model: LTP ± half-spread; missing strike is a hole, not a stand-in."""

from __future__ import annotations

from datetime import datetime

from exitlab.clock import IST, ReplayClock
from exitlab.fills import SlippageModel
from exitlab.r3_core import Minute, live_minutes, minutes_to_series
from exitlab.types import Entry


def _entry() -> Entry:
    return Entry(
        entry_id="e",
        ts=datetime(2026, 9, 17, 10, 0, tzinfo=IST),
        side="CE",
        strike=23200.0,
        entry_price=100.0,
        lots=1,
        lot_size=65,
        entry_set="test",
        session="2026-09-17",
        moneyness="ATM",
    )


def test_minutes_to_series_fill_pays_half_spread() -> None:
    t = datetime(2026, 9, 17, 10, 5, tzinfo=IST)
    mins = [Minute(ts=t, available_ts=t, ltp=100.0, spread=0.40, hole=False)]
    quotes, _ = minutes_to_series(mins)
    clock = ReplayClock(t)
    model = SlippageModel(moneyness="ATM")
    assert model.entry_px(quotes[0], None, clock) == 100.20
    assert model.exit_px(quotes[0], None, clock) == 99.80
    x2 = SlippageModel(moneyness="ATM", spread_mult=2.0)
    assert x2.exit_px(quotes[0], None, clock) == 99.60


def test_live_minutes_missing_strike_is_hole() -> None:
    entry = _entry()
    ticks = [
        {
            "available_ts": datetime(2026, 9, 17, 10, 1, tzinfo=IST),
            "atm_strike": 23300.0,
            "atm_ce": 180.0,
            "itm_ce_strike": 23100.0,
            "itm_ce": 260.0,
            "index": 23310.0,
            "wing_quotes": {},
        }
    ]
    mins = live_minutes(entry, ticks)
    assert mins
    assert mins[0].hole is True
    assert mins[0].ltp is None
    quotes, bars = minutes_to_series(mins)
    assert quotes == []
    assert bars == []
