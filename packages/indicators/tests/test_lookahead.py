"""Lookahead tests for the feature engine (REG-01b, REG-01c, REG-01d).

Feeds only closed bars from V2-03 ``BarBuilder`` and reuses
``marketdata.lookahead.lookahead_failures`` on every emission.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import pytest
from marketdata.bars import BarBuilder
from marketdata.clock import IST
from marketdata.lookahead import lookahead_failures
from marketdata.sources import ListSource
from marketdata.types import BarClosed, SimClock, Tick

from indicators.engine import FeatureEngine
from indicators.view import LookAheadError


def _ticks(base_time: datetime, n: int, ltp_fn) -> list[Tick]:
    out: list[Tick] = []
    for i in range(n):
        ts = base_time + timedelta(seconds=i)
        out.append(
            Tick(
                instrument_id="NIFTY",
                ltp=ltp_fn(i),
                ltq=10,
                volume=10,
                oi=1000,
                exchange_ts=ts.isoformat(),
            )
        )
    return out


def _run_engine(ticks: list[Tick], base_time: datetime) -> tuple[FeatureEngine, list[tuple[BarClosed, datetime]]]:
    clock = SimClock(base_time)
    source = ListSource(ticks, clock)
    builder = BarBuilder()
    engine = FeatureEngine()
    emissions: list[tuple[BarClosed, datetime]] = []
    for event in source.events():
        if event.event_type == "TICK":
            bars = builder.on_tick(event.payload, event.available_ts)
        elif event.event_type == "CLOCK":
            bars = builder.on_clock(event.available_ts)
        else:
            continue
        for bar in bars:
            emissions.append((bar, event.available_ts))
            engine.on_bar(bar, event.available_ts)
    assert lookahead_failures(emissions) == []
    return engine, emissions


def _hand_bar(start: datetime, close: float) -> tuple[BarClosed, datetime]:
    end = start + timedelta(minutes=1)
    available_ts = end + timedelta(seconds=1.5)
    bar = BarClosed(
        instrument_id="NIFTY",
        tf="1m",
        start=start.isoformat(),
        end=end.isoformat(),
        o=22000.0,
        h=22010.0,
        l=21990.0,
        c=close,
        v=1000,
        n_ticks=60,
        available_ts=available_ts.isoformat(),
    )
    return bar, available_ts


def test_random_cut_causality_features() -> None:
    """REG-01b: truncated stream matches full-run features before the cut."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    ticks = _ticks(base_time, 1800, lambda i: 22000.0 + (i % 100))
    engine_full, _ = _run_engine(ticks, base_time)

    for _ in range(5):
        cut_index = random.randint(300, len(ticks) - 300)
        truncated = ticks[:cut_index]
        cut_time = datetime.fromisoformat(truncated[-1].exchange_ts)
        engine_cut, _ = _run_engine(truncated, base_time)
        ema_cut = engine_cut.view(now=cut_time).get("ema20", "NIFTY", "1m")
        ema_full = engine_full.view(now=cut_time).get("ema20", "NIFTY", "1m")
        if ema_cut is not None and ema_full is not None:
            assert abs(ema_cut.value - ema_full.value) < 1e-6


def test_future_poisoning_features() -> None:
    """REG-01c: mutating ticks after T does not change features at or before T."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    original = _ticks(base_time, 1200, lambda i: 22000.0 + (i % 50))
    engine_orig, _ = _run_engine(original, base_time)

    poison_time = base_time + timedelta(minutes=10)
    poison_index = 10 * 60
    poisoned = original[:poison_index] + [
        Tick(
            instrument_id=t.instrument_id,
            ltp=50000.0,
            ltq=t.ltq,
            volume=t.volume,
            oi=t.oi,
            exchange_ts=t.exchange_ts,
        )
        for t in original[poison_index:]
    ]
    engine_poison, _ = _run_engine(poisoned, base_time)

    view_orig = engine_orig.view(now=poison_time)
    view_poison = engine_poison.view(now=poison_time)
    ema_orig = view_orig.get("ema20", "NIFTY", "1m")
    ema_poison = view_poison.get("ema20", "NIFTY", "1m")
    if ema_orig is not None and ema_poison is not None:
        assert abs(ema_orig.value - ema_poison.value) < 1e-6
    atr_orig = view_orig.get("atr", "NIFTY", "1m")
    atr_poison = view_poison.get("atr", "NIFTY", "1m")
    if atr_orig is not None and atr_poison is not None:
        assert abs(atr_orig.value - atr_poison.value) < 1e-6


def test_strict_view_with_planted_future_value() -> None:
    """REG-01d: strict view raises on a planted future value."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()
    for i in range(10):
        bar, available_ts = _hand_bar(base_time + timedelta(minutes=i), 22000.0 + i)
        engine.on_bar(bar, available_ts)

    now = base_time + timedelta(seconds=30)
    view = engine.view(now=now, strict=True)
    with pytest.raises(LookAheadError):
        view.get("ema20", "NIFTY", "1m", now=now)


def test_lookup_counter_zero_on_valid_fixtures() -> None:
    """REG-01d: lookup counter is 0 on fixtures with no look-ahead."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()
    for i in range(20):
        bar, available_ts = _hand_bar(base_time + timedelta(minutes=i), 22000.0 + i)
        engine.on_bar(bar, available_ts)

    now = base_time + timedelta(minutes=25)
    view = engine.view(now=now, strict=True)
    for _ in range(10):
        view.get("ema20", "NIFTY", "1m", now=now)
        view.get("atr", "NIFTY", "1m", now=now)
        view.get("vwap", "NIFTY", "1m", now=now)

    assert view.future_lookup_count == 0
    assert view.lookup_count == 30


def test_oi_lagged_future_poisoning() -> None:
    """REG-01c: OI change ignores updates at or after the decision time."""
    base_time = datetime(2026, 1, 2, 10, 0, 0, tzinfo=IST)
    engine_orig = FeatureEngine()
    engine_orig.on_oi_update("NIFTY", 1000, base_time)
    engine_orig.on_oi_update("NIFTY", 1050, base_time + timedelta(seconds=30))
    engine_orig.on_oi_update("NIFTY", 1100, base_time + timedelta(seconds=60))
    engine_orig.on_oi_update("NIFTY", 1150, base_time + timedelta(seconds=90))

    engine_poison = FeatureEngine()
    engine_poison.on_oi_update("NIFTY", 1000, base_time)
    engine_poison.on_oi_update("NIFTY", 1050, base_time + timedelta(seconds=30))
    engine_poison.on_oi_update("NIFTY", 1100, base_time + timedelta(seconds=60))
    engine_poison.on_oi_update("NIFTY", 9999, base_time + timedelta(seconds=90))

    decision_ts = base_time + timedelta(seconds=60)
    change_orig = engine_orig.get_oi_change("NIFTY", decision_ts, lookback_bars=1)
    change_poison = engine_poison.get_oi_change("NIFTY", decision_ts, lookback_bars=1)
    assert change_orig == change_poison
    assert change_orig == 50.0


def test_builder_emissions_have_no_lookahead() -> None:
    """Every closed bar fed to the engine passes V2-03 lookahead_failures."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    ticks = _ticks(base_time, 600, lambda i: 22000.0 + (i % 20))
    _engine, emissions = _run_engine(ticks, base_time)
    assert emissions
    assert lookahead_failures(emissions) == []
    for bar, when in emissions:
        assert when.isoformat() >= bar.end
        assert bar.available_ts >= bar.end
