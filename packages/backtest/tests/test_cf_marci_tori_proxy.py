"""Unit tests for Marci/Tori CF OHLC proxies — no edge claim."""

from datetime import datetime, timedelta, timezone

from backtest_engine.cf_marci_tori_proxy import (
    lean_cf_marci_bb_reality,
    lean_cf_marci_rizzy_ext,
    lean_cf_tori_tl_bounce,
    lean_cf_tori_tl_break,
)
from backtest_engine.indicators import Bar

IST = timezone(timedelta(hours=5, minutes=30))


def _ts(day: int, hour: int, minute: int = 0) -> int:
    return int(datetime(2026, 9, day, hour, minute, tzinfo=IST).timestamp())


def _bar(ts: int, o: float, h: float, l: float, c: float, v: float = 10) -> Bar:
    return Bar(ts=ts, open=o, high=h, low=l, close=c, volume=v)


def test_marci_rizzy_length():
    bars = [_bar(_ts(1, 10, i % 60), 100 + (i % 5), 102, 98, 100, 5) for i in range(50)]
    leans = lean_cf_marci_rizzy_ext(bars)
    assert len(leans) == len(bars)


def test_marci_bb_reality_length():
    bars = []
    for i in range(40):
        px = 100.0 + (0.5 if i < 25 else -2.0)
        bars.append(_bar(_ts(1, 10, i), px, px + 1, px - 1, px, 5))
    leans = lean_cf_marci_bb_reality(bars)
    assert len(leans) == len(bars)


def test_tori_bounce_length():
    bars = [_bar(_ts(1, 10, i), 100 + i * 0.1, 101 + i * 0.1, 99 + i * 0.1, 100 + i * 0.1, 5) for i in range(40)]
    leans = lean_cf_tori_tl_bounce(bars)
    assert len(leans) == len(bars)


def test_tori_break_length():
    bars = [_bar(_ts(1, 10, i), 100, 101, 99, 100, 5) for i in range(40)]
    leans = lean_cf_tori_tl_break(bars)
    assert len(leans) == len(bars)
