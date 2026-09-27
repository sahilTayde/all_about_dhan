"""Tests for core indicators (batch reference, incremental correctness)."""

import math
from datetime import UTC, datetime, timedelta

import pytest
from marketdata.clock import IST

from indicators.core import ATR, EMA, VWAP, OIChange, RealizedVol


def test_ema_matches_batch_reference() -> None:
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


def test_atr_matches_batch_reference() -> None:
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


def test_vwap_with_volume() -> None:
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


def test_vwap_fallback_to_twap() -> None:
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


def test_vwap_zero_volume_mid_session_does_not_corrupt() -> None:
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


def test_vwap_reset_clears_all_accumulators() -> None:
    """reset() clears VWAP and TWAP accumulators so a new session starts clean."""
    vwap = VWAP()
    vwap.update(10.0, 100.0)
    vwap.update(20.0, 100.0)
    vwap.update(float("nan"), 100.0)
    vwap.reset()
    assert vwap.sum_pv == 0.0
    assert vwap.sum_v == 0.0
    assert vwap.sum_p == 0.0
    assert vwap.n_bars == 0
    assert vwap.seen_volume is False
    assert vwap.vwap_rejected_bars == 0
    val, mode = vwap.update(7.0, None)
    assert mode == "twap"
    assert val == 7.0


def test_vwap_skips_nan_price_and_stays_clean() -> None:
    """A NaN-price bar is rejected; VWAP stays the clean-bar value 15.0."""
    vwap = VWAP()
    v1, m1 = vwap.update(10.0, 100.0)
    assert m1 == "vwap"
    assert v1 == 10.0
    v2, m2 = vwap.update(float("nan"), 100.0)
    assert m2 == "vwap"
    assert v2 == 10.0
    assert vwap.vwap_rejected_bars == 1
    v3, m3 = vwap.update(20.0, 100.0)
    assert m3 == "vwap"
    assert v3 == 15.0
    assert vwap.vwap_rejected_bars == 1


def test_vwap_skips_inf_price_and_stays_clean() -> None:
    """An inf-price bar is rejected the same way as NaN; VWAP stays 15.0."""
    vwap = VWAP()
    vwap.update(10.0, 100.0)
    v2, m2 = vwap.update(float("inf"), 100.0)
    assert m2 == "vwap"
    assert v2 == 10.0
    assert vwap.vwap_rejected_bars == 1
    v3, m3 = vwap.update(20.0, 100.0)
    assert m3 == "vwap"
    assert v3 == 15.0
    assert vwap.vwap_rejected_bars == 1


def test_vwap_skips_nonfinite_and_negative_volume() -> None:
    """Inf volume and negative volume are rejected; they do not accumulate."""
    vwap = VWAP()
    vwap.update(10.0, 100.0)
    v_inf, m_inf = vwap.update(999.0, float("inf"))
    assert m_inf == "vwap"
    assert v_inf == 10.0
    v_neg, m_neg = vwap.update(1000.0, -5.0)
    assert m_neg == "vwap"
    assert v_neg == 10.0
    assert vwap.vwap_rejected_bars == 2
    v3, m3 = vwap.update(20.0, 100.0)
    assert m3 == "vwap"
    assert v3 == 15.0


def test_vwap_nan_before_any_volume_does_not_break_twap() -> None:
    """A leading NaN bar must not break the TWAP fallback."""
    vwap = VWAP()
    val, mode = vwap.update(float("nan"), None)
    assert val is None
    assert vwap.vwap_rejected_bars == 1
    assert vwap.seen_volume is False
    v1, m1 = vwap.update(10.0, None)
    assert m1 == "twap"
    assert v1 == 10.0
    v2, m2 = vwap.update(20.0, None)
    assert m2 == "twap"
    assert v2 == 15.0
    # NaN with volume before any accepted volume bar also stays on TWAP.
    vwap2 = VWAP()
    vwap2.update(float("nan"), 100.0)
    val2, mode2 = vwap2.update(10.0, None)
    assert mode2 == "twap"
    assert val2 == 10.0
    assert vwap2.seen_volume is False


def test_realized_vol_matches_batch() -> None:
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
        result: list[float | None] = []
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


def test_oi_change_lagged_strictly_before_decision_minute() -> None:
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


def test_oi_change_lookback() -> None:
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


def test_realized_vol_skips_nonpositive_close() -> None:
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


def test_realized_vol_skips_nan_and_inf_close() -> None:
    """NaN and inf closes are skipped the same way as <=0; prev_close stays clean."""
    rv = RealizedVol(period=5)
    assert rv.update(100.0) is None
    assert rv.update(float("nan")) is None
    assert rv.update(float("inf")) is None
    assert rv.prev_close == 100.0
    later = rv.update(102.0)
    assert later is None  # one valid return (100 -> 102)
    rv.update(101.0)
    assert rv.value is not None
    assert math.isfinite(rv.value)


def test_oi_naive_timestamp_rejected_at_ingest() -> None:
    """Naive OI timestamps raise ValueError at add, not later at compare time."""
    oi_tracker = OIChange()
    naive = datetime(2026, 1, 2, 10, 4, 50)
    with pytest.raises(ValueError, match="timezone-aware"):
        oi_tracker.update("NIFTY", 1000, naive)
    assert oi_tracker.oi_history == {}


def test_oi_utc_converted_and_cut_off_by_ist_minute() -> None:
    """UTC snapshots convert to IST; 10:05:30 IST excludes 04:35:10Z, includes 04:34:50Z."""
    oi_tracker = OIChange()
    t_prior = datetime(2026, 1, 2, 4, 33, 0, tzinfo=UTC)  # 10:03:00 IST
    t_last = datetime(2026, 1, 2, 4, 34, 50, tzinfo=UTC)  # 10:04:50 IST
    t_in_minute = datetime(2026, 1, 2, 4, 35, 10, tzinfo=UTC)  # 10:05:10 IST
    oi_tracker.update("NIFTY", 1000, t_prior)
    oi_tracker.update("NIFTY", 1100, t_last)
    oi_tracker.update("NIFTY", 9999, t_in_minute)

    for ts, _oi in oi_tracker.oi_history["NIFTY"]:
        assert ts.tzinfo is not None
        assert ts.utcoffset() == timedelta(hours=5, minutes=30)

    decision_ts = datetime(2026, 1, 2, 10, 5, 30, tzinfo=IST)
    change = oi_tracker.get_lagged_change("NIFTY", decision_ts, lookback_bars=1)
    assert change == 100.0


def test_oi_ist_aware_input_unchanged() -> None:
    """IST-aware snapshots stay IST and still use the minute floor."""
    oi_tracker = OIChange()
    t_prior = datetime(2026, 1, 2, 10, 3, 0, tzinfo=IST)
    t_last = datetime(2026, 1, 2, 10, 4, 50, tzinfo=IST)
    t_in_minute = datetime(2026, 1, 2, 10, 5, 10, tzinfo=IST)
    oi_tracker.update("NIFTY", 1000, t_prior)
    oi_tracker.update("NIFTY", 1100, t_last)
    oi_tracker.update("NIFTY", 9999, t_in_minute)
    stored = [ts for ts, _oi in oi_tracker.oi_history["NIFTY"]]
    assert stored[0] == t_prior
    decision_ts = datetime(2026, 1, 2, 10, 5, 30, tzinfo=IST)
    assert oi_tracker.get_lagged_change("NIFTY", decision_ts, lookback_bars=1) == 100.0


def test_oi_naive_decision_ts_raises() -> None:
    """Naive decision_ts raises ValueError at query time (same contract as view now)."""
    oi_tracker = OIChange()
    oi_tracker.update("NIFTY", 1000, datetime(2026, 1, 2, 10, 4, 50, tzinfo=IST))
    with pytest.raises(ValueError, match="decision_ts"):
        oi_tracker.get_lagged_change("NIFTY", datetime(2026, 1, 2, 10, 5, 30))
