"""
Lookahead tests for feature engine (REG-01b, REG-01c, REG-01d).

Uses random-cut causality and future poisoning harness from V2-03.
"""

import random
from datetime import datetime, timedelta

import pytest
from contracts.clock import IST, SimClock
from contracts.payloads import BarClosed, Tick
from marketdata.bars import BarBuilder
from marketdata.sources import ListSource

from indicators.engine import FeatureEngine
from indicators.view import LookAheadError


def test_random_cut_causality_features():
    """
    REG-01b: Random-cut causality on features.

    Features computed from a truncated stream must match the full stream
    for all bars before the cut point.
    """
    # Generate synthetic tick stream (30 minutes)
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    ticks = []
    for i in range(1800):
        ts = base_time + timedelta(seconds=i)
        tick = Tick(
            instrument_id="NIFTY",
            ltp=22000.0 + (i % 100),
            ltq=10,
            volume=10,
            oi=1000,
            exchange_ts=ts.isoformat(),
        )
        ticks.append(tick)

    # Full run
    clock_full = SimClock(base_time)
    source_full = ListSource(ticks, clock_full)
    builder_full = BarBuilder()
    engine_full = FeatureEngine()

    for event in source_full.events():
        if event.event_type == "TICK":
            bars = builder_full.on_tick(event.payload, event.available_ts)
            for bar in bars:
                engine_full.on_bar(bar, event.available_ts)
        elif event.event_type == "CLOCK":
            bars = builder_full.on_clock(event.available_ts)
            for bar in bars:
                engine_full.on_bar(bar, event.available_ts)

    # Get full features
    view_full = engine_full.view()

    # Random cuts (test 5 random cut points)
    for _ in range(5):
        cut_index = random.randint(300, len(ticks) - 300)
        truncated_ticks = ticks[:cut_index]
        cut_time = datetime.fromisoformat(truncated_ticks[-1].exchange_ts)

        clock_cut = SimClock(base_time)
        source_cut = ListSource(truncated_ticks, clock_cut)
        builder_cut = BarBuilder()
        engine_cut = FeatureEngine()

        for event in source_cut.events():
            if event.event_type == "TICK":
                bars = builder_cut.on_tick(event.payload, event.available_ts)
                for bar in bars:
                    engine_cut.on_bar(bar, event.available_ts)
            elif event.event_type == "CLOCK":
                bars = builder_cut.on_clock(event.available_ts)
                for bar in bars:
                    engine_cut.on_bar(bar, event.available_ts)

        # Compare features at cut time
        view_cut = engine_cut.view(now=cut_time)

        # Check EMA20 (if available in both)
        ema_full = view_full.get("ema20", "NIFTY", "1m")
        ema_cut = view_cut.get("ema20", "NIFTY", "1m")

        if ema_full is not None and ema_cut is not None and ema_cut.available_ts <= cut_time:
            # If cut run has an EMA, it should match full run at that time
            # Find corresponding full feature
            full_ema_at_cut_time = None
            view_full_at_cut = engine_full.view(now=cut_time)
            full_ema_at_cut_time = view_full_at_cut.get("ema20", "NIFTY", "1m")

            if full_ema_at_cut_time is not None:
                assert abs(ema_cut.value - full_ema_at_cut_time.value) < 1e-6, (
                    f"EMA mismatch at cut: {ema_cut.value} vs {full_ema_at_cut_time.value}"
                )


def test_future_poisoning_features():
    """
    REG-01c: Future poisoning on features.

    Mutate bars after time T. Features at or before T must not change.
    """
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)

    # Original tick stream (20 minutes)
    original_ticks = []
    for i in range(1200):
        ts = base_time + timedelta(seconds=i)
        tick = Tick(
            instrument_id="NIFTY",
            ltp=22000.0 + (i % 50),
            ltq=10,
            volume=10,
            oi=1000,
            exchange_ts=ts.isoformat(),
        )
        original_ticks.append(tick)

    # Run with original ticks
    clock_orig = SimClock(base_time)
    source_orig = ListSource(original_ticks, clock_orig)
    builder_orig = BarBuilder()
    engine_orig = FeatureEngine()

    for event in source_orig.events():
        if event.event_type == "TICK":
            bars = builder_orig.on_tick(event.payload, event.available_ts)
            for bar in bars:
                engine_orig.on_bar(bar, event.available_ts)
        elif event.event_type == "CLOCK":
            bars = builder_orig.on_clock(event.available_ts)
            for bar in bars:
                engine_orig.on_bar(bar, event.available_ts)

    # Poison time T = 10 minutes
    poison_time = base_time + timedelta(minutes=10)
    poison_index = 10 * 60

    # Mutate ticks after T
    poisoned_ticks = (
        original_ticks[:poison_index]
        + [
            Tick(
                instrument_id=t.instrument_id,
                ltp=50000.0,  # Drastically different
                ltq=t.ltq,
                volume=t.volume,
                oi=t.oi,
                exchange_ts=t.exchange_ts,
            )
            for t in original_ticks[poison_index:]
        ]
    )

    # Run with poisoned ticks
    clock_poison = SimClock(base_time)
    source_poison = ListSource(poisoned_ticks, clock_poison)
    builder_poison = BarBuilder()
    engine_poison = FeatureEngine()

    for event in source_poison.events():
        if event.event_type == "TICK":
            bars = builder_poison.on_tick(event.payload, event.available_ts)
            for bar in bars:
                engine_poison.on_bar(bar, event.available_ts)
        elif event.event_type == "CLOCK":
            bars = builder_poison.on_clock(event.available_ts)
            for bar in bars:
                engine_poison.on_bar(bar, event.available_ts)

    # Features at or before poison time should be identical
    view_orig = engine_orig.view(now=poison_time)
    view_poison = engine_poison.view(now=poison_time)

    # Check EMA20
    ema_orig = view_orig.get("ema20", "NIFTY", "1m")
    ema_poison = view_poison.get("ema20", "NIFTY", "1m")

    if ema_orig is not None and ema_poison is not None:
        assert abs(ema_orig.value - ema_poison.value) < 1e-6, (
            f"EMA changed after poisoning: {ema_orig.value} vs {ema_poison.value}"
        )

    # Check ATR
    atr_orig = view_orig.get("atr", "NIFTY", "1m")
    atr_poison = view_poison.get("atr", "NIFTY", "1m")

    if atr_orig is not None and atr_poison is not None:
        assert abs(atr_orig.value - atr_poison.value) < 1e-6, (
            f"ATR changed after poisoning: {atr_orig.value} vs {atr_poison.value}"
        )


def test_strict_view_with_planted_future_value():
    """
    REG-01d: Strict view raises on planted future value.

    This demonstrates the harness can catch look-ahead bugs.
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

    # Try to access feature at a time before it was available
    now = base_time + timedelta(seconds=30)  # Before first bar closed
    view = engine.view(now=now, strict=True)

    # This should raise because no features are available yet
    with pytest.raises(LookAheadError):
        view.get("ema20", "NIFTY", "1m", now=now)


def test_lookup_counter_zero_on_valid_fixtures():
    """
    REG-01d: Lookup counter is 0 on fixtures with no look-ahead.
    """
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    # Generate bars
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
            h=22010.0,
            l=21990.0,
            c=22000.0 + i,
            v=1000,
            n_ticks=60,
        )
        engine.on_bar(bar, available_ts)

    # Access features with strict view (valid accesses only)
    now = base_time + timedelta(minutes=25)
    view = engine.view(now=now, strict=True)

    # Access multiple features
    for _ in range(10):
        view.get("ema20", "NIFTY", "1m", now=now)
        view.get("atr", "NIFTY", "1m", now=now)
        view.get("vwap", "NIFTY", "1m", now=now)

    # Future lookup counter should be 0
    assert view.future_lookup_count == 0, f"Future lookups detected: {view.future_lookup_count}"
    assert view.lookup_count == 30  # 10 iterations × 3 features


def test_oi_lagged_future_poisoning():
    """
    REG-01c: OI change is immune to future poisoning.

    OI updates after decision time should not affect lagged OI change.
    """
    base_time = datetime(2026, 1, 2, 10, 0, 0, tzinfo=IST)

    # Original OI stream
    engine_orig = FeatureEngine()
    engine_orig.on_oi_update("NIFTY", 1000, base_time)
    engine_orig.on_oi_update("NIFTY", 1050, base_time + timedelta(seconds=30))
    engine_orig.on_oi_update("NIFTY", 1100, base_time + timedelta(seconds=60))
    engine_orig.on_oi_update("NIFTY", 1150, base_time + timedelta(seconds=90))

    # Poisoned OI stream (different values after 60s)
    engine_poison = FeatureEngine()
    engine_poison.on_oi_update("NIFTY", 1000, base_time)
    engine_poison.on_oi_update("NIFTY", 1050, base_time + timedelta(seconds=30))
    engine_poison.on_oi_update("NIFTY", 1100, base_time + timedelta(seconds=60))
    engine_poison.on_oi_update("NIFTY", 9999, base_time + timedelta(seconds=90))  # Poisoned

    # Decision at 60s
    decision_ts = base_time + timedelta(seconds=60)

    # OI change should be identical (both see only up to 30s)
    change_orig = engine_orig.get_oi_change("NIFTY", decision_ts, lookback_bars=1)
    change_poison = engine_poison.get_oi_change("NIFTY", decision_ts, lookback_bars=1)

    assert change_orig == change_poison, (
        f"OI change affected by future: {change_orig} vs {change_poison}"
    )
    assert change_orig == 50.0  # 1100 - 1050
