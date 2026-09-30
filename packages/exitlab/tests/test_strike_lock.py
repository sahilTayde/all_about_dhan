"""Fixed-strike marks only. Never the rolling ATM/ITM contract."""

from __future__ import annotations

from datetime import datetime

from exitlab.clock import IST
from exitlab.entries import random_entries
from exitlab.research import _series_for_live
from exitlab.tapes import strike_ltp
from exitlab.types import Entry


def _ts(h: int, m: int) -> datetime:
    return datetime(2026, 9, 17, h, m, tzinfo=IST)


def _tick(*, atm: float, wings: dict[str, dict[str, float]], itm_ce: float = 23200.0) -> dict:
    return {
        "available_ts": _ts(10, 10),
        "index": atm + 3,
        "atm_strike": atm,
        "atm_ce": 80.0,
        "atm_pe": 70.0,
        "itm_ce": 120.0,
        "itm_pe": 110.0,
        "itm_ce_strike": itm_ce,
        "itm_pe_strike": atm + 100,
        "wing_quotes": wings,
        "expiry": "2026-09-22",
        "stale": False,
    }


def test_strike_ltp_ignores_rolling_itm() -> None:
    tick = _tick(atm=23300.0, wings={"23100": {"ce": 200.0, "pe": 15.0}}, itm_ce=23250.0)
    assert strike_ltp(tick, side="CE", strike=23100.0) == 200.0
    assert strike_ltp(tick, side="CE", strike=23200.0) is None  # not this strike
    assert strike_ltp(tick, side="CE", strike=23300.0) == 80.0  # ATM field matches


def test_series_skips_missing_strike_does_not_mark_roll() -> None:
    entry = Entry(
        entry_id="x",
        ts=_ts(10, 10),
        side="CE",
        strike=23100.0,
        entry_price=200.0,
        lots=1,
        lot_size=65,
        entry_set="test",
        session="2026-09-17",
        moneyness="ITM200",
    )
    ticks = [
        _tick(atm=23300.0, wings={}),  # no 23100 — must skip
        {
            **_tick(atm=23350.0, wings={"23100": {"ce": 190.0}}),
            "available_ts": _ts(10, 11),
        },
    ]
    quotes, _, _ = _series_for_live(entry, ticks)
    assert len(quotes) == 1
    assert quotes[0].ltp == 190.0
    assert quotes[0].strike == 23100.0


def test_random_entries_drop_missing_strike() -> None:
    # Intended ITM200 CE = atm-200 = 23100, not in wings and not the rolling ITM.
    tick = _tick(atm=23300.0, wings={"23300": {"ce": 80.0, "pe": 70.0}}, itm_ce=23200.0)
    # Repeat so ATM and ITM100 can fill; ITM200 must be dropped, not repriced to 23200.
    ticks = [tick] * 40
    out = random_entries(ticks, session="2026-09-17", scenario="chop", seed=1, n=12)
    assert out
    assert all(e.strike != 23200.0 or e.moneyness != "ITM200" for e in out)
    for e in out:
        assert strike_ltp(tick, side=e.side, strike=e.strike) is not None
