"""Tests for FeatureEngine and FeatureView."""

from datetime import datetime, timedelta

import pytest
from marketdata.clock import IST
from marketdata.types import BarClosed

from indicators.engine import FeatureEngine
from indicators.view import LookAheadError


def _bar(
    start: datetime,
    close: float,
    *,
    high: float = 22010.0,
    low: float = 21990.0,
) -> tuple[BarClosed, datetime]:
    end = start + timedelta(minutes=1)
    available_ts = end + timedelta(seconds=1.5)
    bar = BarClosed(
        instrument_id="NIFTY",
        tf="1m",
        start=start.isoformat(),
        end=end.isoformat(),
        o=22000.0,
        h=high,
        l=low,
        c=close,
        v=1000,
        n_ticks=60,
        available_ts=available_ts.isoformat(),
    )
    return bar, available_ts


def test_feature_engine_ema() -> None:
    """FeatureEngine computes EMA20."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    for i in range(30):
        bar, available_ts = _bar(base_time + timedelta(minutes=i), 22000.0 + i)
        engine.on_bar(bar, available_ts)

    ema_val = engine.view().get("ema20", "NIFTY", "1m")
    assert ema_val is not None
    assert ema_val.value > 0.0


def test_feature_engine_atr() -> None:
    """FeatureEngine computes ATR."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    for i in range(20):
        bar, available_ts = _bar(
            base_time + timedelta(minutes=i),
            22000.0,
            high=22000.0 + 50 + i,
            low=22000.0 - 50 - i,
        )
        engine.on_bar(bar, available_ts)

    atr_val = engine.view().get("atr", "NIFTY", "1m")
    assert atr_val is not None
    assert atr_val.value > 0.0


def test_feature_engine_vwap() -> None:
    """FeatureEngine computes VWAP."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    for i in range(10):
        bar, available_ts = _bar(base_time + timedelta(minutes=i), 22000.0)
        engine.on_bar(bar, available_ts)

    vwap_val = engine.view().get("vwap", "NIFTY", "1m")
    assert vwap_val is not None
    assert vwap_val.value > 0.0


def test_feature_view_strict_mode_raises_on_future() -> None:
    """FeatureView strict mode raises LookAheadError on future access (REG-01d)."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()
    bar, available_ts = _bar(base_time, 22000.0)
    engine.on_bar(bar, available_ts)

    now = base_time + timedelta(seconds=30)
    view = engine.view(now=now, strict=True)
    with pytest.raises(LookAheadError):
        view.get("ema20", "NIFTY", "1m", now=now)


def test_feature_view_strict_mode_lookup_counter_zero() -> None:
    """Strict mode lookup counter is 0 when no future lookups (REG-01d)."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    for i in range(10):
        bar, available_ts = _bar(base_time + timedelta(minutes=i), 22000.0 + i)
        engine.on_bar(bar, available_ts)

    now = base_time + timedelta(minutes=20)
    view = engine.view(now=now, strict=True)
    for _ in range(10):
        view.get("ema20", "NIFTY", "1m", now=now)

    assert view.future_lookup_count == 0
    assert view.lookup_count == 10


def test_feature_view_filters_by_now() -> None:
    """FeatureView filters features to only those available at 'now'."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    for i in range(5):
        bar, available_ts = _bar(base_time + timedelta(minutes=i), 22000.0 + i)
        engine.on_bar(bar, available_ts)

    now = base_time + timedelta(minutes=25)
    view = engine.view(now=now, strict=False)
    assert view.get("ema20", "NIFTY", "1m") is not None

    now_early = base_time + timedelta(seconds=30)
    view_early = engine.view(now=now_early, strict=False)
    assert view_early.get("ema20", "NIFTY", "1m") is None


def test_oi_change_in_engine() -> None:
    """FeatureEngine tracks OI change with strict lag."""
    base_time = datetime(2026, 1, 2, 10, 0, 0, tzinfo=IST)
    engine = FeatureEngine()

    engine.on_oi_update("NIFTY", 1000, base_time)
    engine.on_oi_update("NIFTY", 1050, base_time + timedelta(seconds=30))
    engine.on_oi_update("NIFTY", 1100, base_time + timedelta(seconds=60))
    engine.on_oi_update("NIFTY", 1200, base_time + timedelta(seconds=90))

    decision_ts = base_time + timedelta(seconds=90)
    change = engine.get_oi_change("NIFTY", decision_ts, lookback_bars=1)
    assert change == 50.0
