"""Tests for FeatureEngine and FeatureView."""

from datetime import datetime, timedelta

import pytest
from contracts.clock import IST
from contracts.payloads import BarClosed

from indicators.engine import FeatureEngine
from indicators.view import LookAheadError


def test_feature_engine_ema():
    """FeatureEngine computes EMA20."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    # Generate 30 bars
    for i in range(30):
        bar_start = base_time + timedelta(minutes=i)
        bar_end = bar_start + timedelta(minutes=1)
        available_ts = bar_end + timedelta(seconds=1.5)

        bar = BarClosed(
            instrument_id="NIFTY",
            tf="1m",
            start=bar_start.isoformat(),
            end=bar_end.isoformat(),
            o=22000.0,
            h=22010.0,
            l=21990.0,
            c=22000.0 + i,
            v=1000,
            n_ticks=60,
        )
        engine.on_bar(bar, available_ts)

    # Check EMA20 exists
    view = engine.view()
    ema_val = view.get("ema20", "NIFTY", "1m")
    assert ema_val is not None
    assert ema_val.value > 0.0


def test_feature_engine_atr():
    """FeatureEngine computes ATR."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    # Generate bars with varying ranges
    for i in range(20):
        bar_start = base_time + timedelta(minutes=i)
        bar_end = bar_start + timedelta(minutes=1)
        available_ts = bar_end + timedelta(seconds=1.5)

        bar = BarClosed(
            instrument_id="NIFTY",
            tf="1m",
            start=bar_start.isoformat(),
            end=bar_end.isoformat(),
            o=22000.0,
            h=22000.0 + 50 + i,
            l=22000.0 - 50 - i,
            c=22000.0,
            v=1000,
            n_ticks=60,
        )
        engine.on_bar(bar, available_ts)

    # Check ATR exists
    view = engine.view()
    atr_val = view.get("atr", "NIFTY", "1m")
    assert atr_val is not None
    assert atr_val.value > 0.0


def test_feature_engine_vwap():
    """FeatureEngine computes VWAP."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    # Generate bars
    for i in range(10):
        bar_start = base_time + timedelta(minutes=i)
        bar_end = bar_start + timedelta(minutes=1)
        available_ts = bar_end + timedelta(seconds=1.5)

        bar = BarClosed(
            instrument_id="NIFTY",
            tf="1m",
            start=bar_start.isoformat(),
            end=bar_end.isoformat(),
            o=22000.0,
            h=22010.0,
            l=21990.0,
            c=22000.0,
            v=1000,
            n_ticks=60,
        )
        engine.on_bar(bar, available_ts)

    # Check VWAP exists
    view = engine.view()
    vwap_val = view.get("vwap", "NIFTY", "1m")
    assert vwap_val is not None
    assert vwap_val.value > 0.0


def test_feature_view_strict_mode_raises_on_future():
    """FeatureView strict mode raises LookAheadError on future access (REG-01d)."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    # Generate one bar
    bar_end = base_time + timedelta(minutes=1)
    available_ts = bar_end + timedelta(seconds=1.5)

    bar = BarClosed(
        instrument_id="NIFTY",
        tf="1m",
        start=base_time.isoformat(),
        end=bar_end.isoformat(),
        o=22000.0,
        h=22010.0,
        l=21990.0,
        c=22000.0,
        v=1000,
        n_ticks=60,
    )
    engine.on_bar(bar, available_ts)

    # Create strict view with 'now' before the bar's available_ts
    now = base_time + timedelta(seconds=30)  # Before bar closed
    view = engine.view(now=now, strict=True)

    # Accessing feature should raise
    with pytest.raises(LookAheadError):
        view.get("ema20", "NIFTY", "1m", now=now)


def test_feature_view_strict_mode_lookup_counter_zero():
    """
    Strict mode lookup counter is 0 when no future lookups (REG-01d).
    """
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    # Generate bars
    for i in range(10):
        bar_start = base_time + timedelta(minutes=i)
        bar_end = bar_start + timedelta(minutes=1)
        available_ts = bar_end + timedelta(seconds=1.5)

        bar = BarClosed(
            instrument_id="NIFTY",
            tf="1m",
            start=bar_start.isoformat(),
            end=bar_end.isoformat(),
            o=22000.0,
            h=22010.0,
            l=21990.0,
            c=22000.0 + i,
            v=1000,
            n_ticks=60,
        )
        engine.on_bar(bar, available_ts)

    # Create strict view with 'now' after all bars
    now = base_time + timedelta(minutes=20)
    view = engine.view(now=now, strict=True)

    # Access features (all should be valid)
    for i in range(10):
        view.get("ema20", "NIFTY", "1m", now=now)

    # Future lookup counter should be 0
    assert view.future_lookup_count == 0
    assert view.lookup_count == 10


def test_feature_view_filters_by_now():
    """FeatureView filters features to only those available at 'now'."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    # Generate 5 bars
    for i in range(5):
        bar_start = base_time + timedelta(minutes=i)
        bar_end = bar_start + timedelta(minutes=1)
        available_ts = bar_end + timedelta(seconds=1.5)

        bar = BarClosed(
            instrument_id="NIFTY",
            tf="1m",
            start=bar_start.isoformat(),
            end=bar_end.isoformat(),
            o=22000.0,
            h=22010.0,
            l=21990.0,
            c=22000.0 + i,
            v=1000,
            n_ticks=60,
        )
        engine.on_bar(bar, available_ts)

    # View after all bars processed (should have features)
    now = base_time + timedelta(minutes=25)
    view = engine.view(now=now, strict=False)

    ema_val = view.get("ema20", "NIFTY", "1m")
    assert ema_val is not None

    # View at 9:15:30 (before first bar available at 9:16:01.5 - no features yet)
    now_early = base_time + timedelta(seconds=30)
    view_early = engine.view(now=now_early, strict=False)
    ema_val_early = view_early.get("ema20", "NIFTY", "1m")
    assert ema_val_early is None  # No features available yet


def test_oi_change_in_engine():
    """FeatureEngine tracks OI change with strict lag."""
    base_time = datetime(2026, 1, 2, 10, 0, 0, tzinfo=IST)
    engine = FeatureEngine()

    # Record OI updates
    engine.on_oi_update("NIFTY", 1000, base_time)
    engine.on_oi_update("NIFTY", 1050, base_time + timedelta(seconds=30))
    engine.on_oi_update("NIFTY", 1100, base_time + timedelta(seconds=60))
    engine.on_oi_update("NIFTY", 1200, base_time + timedelta(seconds=90))

    # Get OI change at decision time (90s)
    decision_ts = base_time + timedelta(seconds=90)
    change = engine.get_oi_change("NIFTY", decision_ts, lookback_bars=1)

    # Should see up to 60s (1100), not 90s (1200)
    assert change == 50.0
