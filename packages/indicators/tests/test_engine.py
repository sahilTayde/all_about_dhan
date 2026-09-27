"""Tests for FeatureEngine and FeatureView."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

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

    now = base_time + timedelta(minutes=40)
    ema_val = engine.view(now).get("ema20", "NIFTY", "1m")
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

    now = base_time + timedelta(minutes=30)
    atr_val = engine.view(now).get("atr", "NIFTY", "1m")
    assert atr_val is not None
    assert atr_val.value > 0.0


def test_feature_engine_vwap() -> None:
    """FeatureEngine computes VWAP."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()

    for i in range(10):
        bar, available_ts = _bar(base_time + timedelta(minutes=i), 22000.0)
        engine.on_bar(bar, available_ts)

    now = base_time + timedelta(minutes=20)
    vwap_val = engine.view(now).get("vwap", "NIFTY", "1m")
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


def test_view_requires_now() -> None:
    """Unfiltered view is forbidden (now is required)."""
    engine = FeatureEngine()
    with pytest.raises(TypeError):
        engine.view()  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="requires now"):
        engine.view(None)  # type: ignore[arg-type]


def test_view_naive_now_raises() -> None:
    """Naive view(now) raises ValueError; UTC-aware now is converted to IST."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()
    bar, available_ts = _bar(base_time, 22000.0)
    engine.on_bar(bar, available_ts)

    with pytest.raises(ValueError, match="timezone-aware"):
        engine.view(datetime(2026, 1, 2, 9, 20, 0))

    now_utc = datetime(2026, 1, 2, 4, 0, 0, tzinfo=UTC)  # 09:30 IST
    view = engine.view(now_utc)
    assert view.get("ema20", "NIFTY", "1m") is not None


def test_engine_oi_naive_rejected_utc_converted() -> None:
    """on_oi_update rejects naive ts; UTC snapshots follow the IST minute floor."""
    engine = FeatureEngine()
    with pytest.raises(ValueError, match="timezone-aware"):
        engine.on_oi_update("NIFTY", 1000, datetime(2026, 1, 2, 10, 4, 50))

    engine.on_oi_update("NIFTY", 1000, datetime(2026, 1, 2, 4, 33, 0, tzinfo=UTC))
    engine.on_oi_update("NIFTY", 1100, datetime(2026, 1, 2, 4, 34, 50, tzinfo=UTC))
    engine.on_oi_update("NIFTY", 9999, datetime(2026, 1, 2, 4, 35, 10, tzinfo=UTC))
    decision_ts = datetime(2026, 1, 2, 10, 5, 30, tzinfo=IST)
    assert engine.get_oi_change("NIFTY", decision_ts, lookback_bars=1) == 100.0
    # Stored data must not crash view().
    view = engine.view(decision_ts)
    assert view.get("ema20", "NIFTY", "1m") is None


def test_engine_vwap_rejected_bars_exposed() -> None:
    """FeatureEngine.vwap_rejected_bars sums per-session VWAP rejects."""
    base_time = datetime(2026, 1, 2, 9, 15, 0, tzinfo=IST)
    engine = FeatureEngine()
    bar_ok, ts_ok = _bar(base_time, 10.0)
    bar_ok = replace(bar_ok, c=10.0, h=10.0, l=10.0, v=100)
    engine.on_bar(bar_ok, ts_ok)
    bar_nan, ts_nan = _bar(base_time + timedelta(minutes=1), 20.0)
    bar_nan = replace(bar_nan, c=float("nan"), h=float("nan"), l=float("nan"), v=100)
    engine.on_bar(bar_nan, ts_nan)
    assert engine.vwap_rejected_bars == 1


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
