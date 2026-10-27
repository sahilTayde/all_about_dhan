"""Overnight carry + gap-through stop (audit 2026-10-27). Bars after drop_dead_band end at 14:59, so 15:15 never exists."""
from datetime import datetime, timedelta, timezone

from backtest_engine.indicators import Bar
from backtest_engine.simulate import simulate_leans
from backtest_engine.simulate_sltp import _hit_levels

IST = timezone(timedelta(hours=5, minutes=30))


def _ts(day, hh, mm):
    return int(datetime(2026, 10, day, hh, mm, tzinfo=IST).timestamp())


def test_no_overnight_carry():
    bars = [Bar(_ts(21, 14, 50 + k), 100 + k, 101 + k, 99 + k, 100 + k, 0) for k in range(10)]
    bars += [Bar(_ts(22, 9, 31 + k), 150, 151, 149, 150, 0) for k in range(3)]
    tr = simulate_leans(bars, ["CE"] * len(bars), strategy_id="T", underlying="NIFTY")
    assert tr and tr[0].session == "2026-10-21" and tr[0].reason == "flatten_009", tr
    assert tr[0].exit_px < 150  # not the next day's gap


def test_stop_gap_fills_at_open():
    assert _hit_levels("CE", Bar(0, 90, 95, 88, 92, 0), 100.0, 130.0) == ("atr_stop", 90)
    assert _hit_levels("PE", Bar(0, 110, 112, 105, 108, 0), 100.0, 70.0) == ("atr_stop", 110)
    assert _hit_levels("CE", Bar(0, 105, 106, 99, 100, 0), 100.0, 130.0) == ("atr_stop", 100.0)
