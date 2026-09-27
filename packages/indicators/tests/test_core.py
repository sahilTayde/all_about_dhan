"""Tests for core indicators (batch reference, incremental correctness)."""

import math
from datetime import datetime, timedelta

from marketdata.clock import IST

from indicators.core import ATR, EMA, VWAP, OIChange, RealizedVol


def test_ema_matches_batch_reference():
    """EMA incremental matches batch calculation (within 1e-9)."""
    prices = [100.0, 102.0, 101.0, 103.0, 104.0, 103.5, 105.0, 106.0, 105.5, 107.0]
    period = 5

    # Incremental EMA
    ema = EMA(period=period)
    incremental_values = [ema.update(p) for p in prices]

    # Batch reference (simple EMA)
    def batch_ema(prices: list[float], period: int) -> list[float]:
        alpha = 2.0 / (period + 1)
        result = []
        ema_val = prices[0]
        for p in prices:
            ema_val = alpha * p + (1 - alpha) * ema_val
            result.append(ema_val)
        return result

    batch_values = batch_ema(prices, period)

    # Compare
    for i, (inc, batch) in enumerate(zip(incremental_values, batch_values)):
        assert abs(inc - batch) < 1e-9, f"Mismatch at index {i}: {inc} vs {batch}"


def test_atr_matches_batch_reference():
    """ATR incremental matches batch calculation (within 1e-9)."""
    # OHLC bars
    bars = [
        (100.0, 105.0, 99.0, 102.0),
        (102.0, 106.0, 101.0, 104.0),
        (104.0, 108.0, 103.0, 107.0),
        (107.0, 110.0, 106.0, 109.0),
        (109.0, 111.0, 108.0, 110.0),
        (110.0, 112.0, 109.0, 111.0),
        (111.0, 113.0, 110.0, 112.0),
        (112.0, 114.0, 111.0, 113.0),
        (113.0, 115.0, 112.0, 114.0),
        (114.0, 116.0, 113.0, 115.0),
    ]
    period = 5

    # Incremental ATR
    atr = ATR(period=period)
    incremental_values = []
    for _o, high, low, close in bars:
        val = atr.update(high, low, close)
        incremental_values.append(val)

    # Batch reference
    def batch_atr(bars: list[tuple[float, float, float, float]], period: int) -> list[float]:
        true_ranges = []
        for i, (_o, high, low, close) in enumerate(bars):
            if i == 0:
                tr = high - low
            else:
                prev_close = bars[i - 1][3]
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        # Wilder's smoothing (same as EMA with period)
        alpha = 1.0 / period
        atr_val = true_ranges[0]
        result = []
        for tr in true_ranges:
            atr_val = alpha * tr + (1 - alpha) * atr_val
            result.append(atr_val)
        return result

    batch_values = batch_atr(bars, period)

    # Compare
    for i, (inc, batch) in enumerate(zip(incremental_values, batch_values)):
        assert inc is not None
        assert abs(inc - batch) < 1e-9, f"Mismatch at index {i}: {inc} vs {batch}"


def test_vwap_with_volume():
    """VWAP incremental with volume."""
    # (price, volume) pairs
    data = [(100.0, 1000.0), (102.0, 1500.0), (101.0, 1200.0), (103.0, 1800.0)]

    vwap = VWAP()
    incremental_values = []
    for price, volume in data:
        val, mode = vwap.update(price, volume)
        incremental_values.append(val)
        assert mode == "vwap"

    # Batch reference
    sum_pv = 0.0
    sum_v = 0.0
    batch_values = []
    for price, volume in data:
        sum_pv += price * volume
        sum_v += volume
        batch_values.append(sum_pv / sum_v)

    # Compare
    for i, (inc, batch) in enumerate(zip(incremental_values, batch_values)):
        assert inc is not None
        assert abs(inc - batch) < 1e-9, f"Mismatch at index {i}: {inc} vs {batch}"


def test_vwap_fallback_to_twap():
    """All-None volume stays TWAP for the session (index instruments)."""
    prices = [100.0, 102.0, 101.0, 103.0]

    vwap = VWAP()
    incremental_values = []
    for price in prices:
        val, mode = vwap.update(price, volume=None)
        incremental_values.append(val)
        assert mode == "twap"

    batch_values = []
    cumsum = 0.0
    for i, price in enumerate(prices):
        cumsum += price
        batch_values.append(cumsum / (i + 1))

    for i, (inc, batch) in enumerate(zip(incremental_values, batch_values)):
        assert inc is not None
        assert abs(inc - batch) < 1e-9, f"Mismatch at index {i}: {inc} vs {batch}"


def test_vwap_zero_volume_mid_session_does_not_corrupt():
    """A zero-volume bar after volume has been seen is ignored; VWAP stays 15.0."""
    vwap = VWAP()
    v1, m1 = vwap.update(10.0, 100.0)
    assert m1 == "vwap"
    assert v1 == 10.0
    v2, m2 = vwap.update(1000.0, 0.0)
    assert m2 == "vwap"
    assert v2 == 10.0
    v3, m3 = vwap.update(20.0, 100.0)
    assert m3 == "vwap"
    assert v3 == 15.0


def test_vwap_reset_clears_all_accumulators():
    """reset() clears VWAP and TWAP accumulators so a new session starts clean."""
    vwap = VWAP()
    vwap.update(10.0, 100.0)
    vwap.update(20.0, 100.0)
    vwap.reset()
    assert vwap.sum_pv == 0.0
    assert vwap.sum_v == 0.0
    assert vwap.sum_p == 0.0
    assert vwap.n_bars == 0
    assert vwap.seen_volume is False
    val, mode = vwap.update(7.0, None)
    assert mode == "twap"
    assert val == 7.0


def test_realized_vol_matches_batch():
    """Realized vol incremental matches batch calculation."""
    prices = [100.0, 102.0, 101.0, 103.0, 104.0, 103.5, 105.0, 106.0, 105.5, 107.0]
    period = 5

    # Incremental
    rv = RealizedVol(period=period)
    incremental_values = []
    for p in prices:
        val = rv.update(p)
        incremental_values.append(val)

    # Batch reference
    def batch_realized_vol(prices: list[float], period: int) -> list[float | None]:
        result = []
        for i in range(len(prices)):
            if i == 0:
                result.append(None)
                continue

            # Compute log returns up to i
            returns = []
            for j in range(1, i + 1):
                if j > 0:
                    returns.append(math.log(prices[j] / prices[j - 1]))

            # Keep last N returns
            window = returns[-period:] if len(returns) > period else returns

            # Compute std dev
            if len(window) < 2:
                result.append(None)
            else:
                mean_ret = sum(window) / len(window)
                variance = sum((r - mean_ret) ** 2 for r in window) / (len(window) - 1)
                result.append(math.sqrt(variance))

        return result

    batch_values = batch_realized_vol(prices, period)

    # Compare
    for i, (inc, batch) in enumerate(zip(incremental_values, batch_values)):
        if batch is None:
            assert inc is None or i < 2
        else:
            assert inc is not None
            assert abs(inc - batch) < 1e-9, f"Mismatch at index {i}: {inc} vs {batch}"


def test_oi_change_lagged_strictly_before_decision_minute():
    """Decision at 10:05:30 must not see 10:05:10; it must see 10:04:50 (REG-01)."""
    oi_tracker = OIChange()
    t_prior = datetime(2026, 1, 2, 10, 3, 0, tzinfo=IST)
    t_last = datetime(2026, 1, 2, 10, 4, 50, tzinfo=IST)
    t_in_minute = datetime(2026, 1, 2, 10, 5, 10, tzinfo=IST)
    oi_tracker.update("NIFTY", 1000, t_prior)
    oi_tracker.update("NIFTY", 1100, t_last)
    oi_tracker.update("NIFTY", 9999, t_in_minute)

    decision_ts = datetime(2026, 1, 2, 10, 5, 30, tzinfo=IST)
    change = oi_tracker.get_lagged_change("NIFTY", decision_ts, lookback_bars=1)
    assert change == 100.0


def test_oi_change_lookback():
    """OI lookback uses only snapshots before the decision minute."""
    base_time = datetime(2026, 1, 2, 10, 0, 0, tzinfo=IST)
    oi_tracker = OIChange()
    # 10:00, 10:01, 10:02, 10:03, 10:04
    for i, oi in enumerate([1000, 1050, 1100, 1150, 1200]):
        oi_tracker.update("NIFTY", oi, base_time + timedelta(minutes=i))

    decision_ts = datetime(2026, 1, 2, 10, 5, 30, tzinfo=IST)
    change = oi_tracker.get_lagged_change("NIFTY", decision_ts, lookback_bars=2)
    # visible: all five (all < 10:05). current=1200, two back=1100
    assert change == 100.0


def test_realized_vol_skips_nonpositive_close():
    """close<=0 or prev_close<=0 skips the return; no math domain error."""
    rv = RealizedVol(period=5)
    assert rv.update(100.0) is None
    assert rv.update(0.0) is None
    assert rv.update(-5.0) is None
    later = rv.update(102.0)
    assert later is None  # only one valid return so far (100 -> 102)
    rv.update(101.0)
    assert rv.value is not None
    assert rv.value >= 0.0
