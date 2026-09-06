"""Unit tests for Fabio CF OHLC proxies — no edge claim."""

from datetime import datetime, timedelta, timezone

from backtest_engine.fabio_proxy import (
    lean_cf_break_retest_pd,
    lean_cf_failed_auction,
    lean_cf_mr_to_poc,
    prior_session_profile,
)
from backtest_engine.indicators import Bar

IST = timezone(timedelta(hours=5, minutes=30))


def _ts(day: int, hour: int, minute: int = 0) -> int:
    return int(datetime(2026, 9, day, hour, minute, tzinfo=IST).timestamp())


def _bar(ts: int, o: float, h: float, l: float, c: float, v: float = 10) -> Bar:
    return Bar(ts=ts, open=o, high=h, low=l, close=c, volume=v)


def test_failed_auction_pe_after_pdh_sweep():
    # Day 1 range 100-110
    d1 = [_bar(_ts(1, 10, i), 105, 105 + (i % 3), 104, 105, 5) for i in range(10)]
    d1[5] = _bar(_ts(1, 10, 5), 108, 110, 107, 109, 5)
    d1[6] = _bar(_ts(1, 10, 6), 109, 110, 100, 100, 5)
    # Day 2: sweep above 110 then close back
    d2 = [
        _bar(_ts(2, 10, 0), 108, 112, 108, 111, 5),  # touch above PDH
        _bar(_ts(2, 10, 3), 111, 111, 107, 108, 5),  # close back inside → PE
    ]
    leans = lean_cf_failed_auction(d1 + d2, confirm_bars=5)
    assert leans[-1] == "PE"


def test_mr_to_poc_uses_prior_profile():
    d1 = []
    for i in range(20):
        # Cluster volume mid ~100
        px = 100.0 if i < 15 else 108.0
        d1.append(_bar(_ts(1, 10, i), px, px + 1, px - 1, px, 50 if i < 15 else 1))
    d2 = [
        _bar(_ts(2, 10, 0), 108, 110, 107, 109, 5),  # above VA
        _bar(_ts(2, 10, 3), 109, 109, 100.0, 100.1, 5),  # reclaim inside VA (stay above VAL) → PE
    ]
    leans = lean_cf_mr_to_poc(d1 + d2)
    assert any(x == "PE" for x in leans)


def test_profile_keys():
    bars = [_bar(_ts(1, 10, i), 100, 101, 99, 100, 10) for i in range(5)]
    bars += [_bar(_ts(2, 10, i), 100, 101, 99, 100, 10) for i in range(5)]
    prof = prior_session_profile(bars)
    assert "2026-09-02" in prof
    assert "poc" in prof["2026-09-02"]


def test_break_retest_skips_first_drive():
    d1 = [_bar(_ts(1, 10, i), 100, 105, 95, 100, 5) for i in range(8)]
    d1[3] = _bar(_ts(1, 10, 3), 100, 110, 100, 108, 5)
    d1[4] = _bar(_ts(1, 10, 4), 108, 110, 95, 96, 5)
    # Day2: break high only (first drive) — should stay SKIP until retest+continue
    d2 = [_bar(_ts(2, 10, 0), 108, 112, 108, 111, 5)]
    leans = lean_cf_break_retest_pd(d1 + d2)
    assert leans[-1] == "SKIP"
