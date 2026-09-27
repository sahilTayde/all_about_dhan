"""V2-05b entry-location acceptance tests (closed 1m bars only)."""

from datetime import datetime, timedelta

from marketdata.clock import IST
from marketdata.types import BarClosed

from indicators.core import EMA
from indicators.engine import FeatureEngine
from indicators.location import (
    LocationTracker,
    candle_50,
    compute_entry_location,
    detect_fvgs,
    signed_distance_atr,
)


def _bar(
    i: int,
    o: float,
    h: float,
    low: float,
    c: float,
    *,
    instrument_id: str = "NIFTY",
    v: int | None = 1000,
    tf: str = "1m",
    base: datetime | None = None,
) -> tuple[BarClosed, datetime]:
    start = (base or datetime(2026, 1, 2, 9, 15, tzinfo=IST)) + timedelta(minutes=i)
    end = start + timedelta(minutes=1)
    available = end + timedelta(seconds=1.5)
    bar = BarClosed(
        instrument_id=instrument_id,
        tf=tf,
        start=start.isoformat(),
        end=end.isoformat(),
        o=o,
        h=h,
        l=low,
        c=c,
        v=v,
        n_ticks=60,
        available_ts=available.isoformat(),
    )
    return bar, available


def _bullish_fvg_triple(i0: int = 0) -> list[tuple[BarClosed, datetime]]:
    # bar1.high=22010 < bar3.low=22040 → bullish FVG [22010, 22040]
    return [
        _bar(i0, 22000, 22010, 21990, 22005),
        _bar(i0 + 1, 22005, 22080, 22000, 22070),
        _bar(i0 + 2, 22070, 22090, 22040, 22060),
    ]


def _bearish_fvg_triple(i0: int = 0) -> list[tuple[BarClosed, datetime]]:
    # bar1.low=22050 > bar3.high=22020 → bearish FVG [22020, 22050]
    return [
        _bar(i0, 22060, 22070, 22050, 22055),
        _bar(i0 + 1, 22055, 22060, 21980, 22000),
        _bar(i0 + 2, 22000, 22020, 21970, 21990),
    ]


def test_bullish_fvg_formed_partial_full_expired():
    """Hand fixture: bullish FVG formed, partly filled, fully filled, expired."""
    formed = [b for b, _ in _bullish_fvg_triple()]
    gaps = detect_fvgs(formed)
    assert len(gaps) == 1
    assert gaps[0].kind == "bullish"
    assert gaps[0].low == 22010
    assert gaps[0].high == 22040
    assert gaps[0].filled == "none"

    partial_bar, _ = _bar(3, 22050, 22055, 22025, 22045)  # low enters gap
    gaps = detect_fvgs(formed + [partial_bar])
    assert len(gaps) == 1 and gaps[0].filled == "partial"

    full_bar, _ = _bar(4, 22040, 22045, 22000, 22010)  # low through gap
    assert detect_fvgs(formed + [partial_bar, full_bar]) == []

    # Expire: 60 bars after formation (age >= 60) without a fill
    aged = formed + [_bar(3 + i, 22080, 22090, 22070, 22080)[0] for i in range(60)]
    assert detect_fvgs(aged) == []
    almost = formed + [_bar(3 + i, 22080, 22090, 22070, 22080)[0] for i in range(59)]
    assert len(detect_fvgs(almost)) == 1


def test_bearish_fvg_formed_partial_full_expired():
    """Hand fixture: bearish FVG formed, partly filled, fully filled, expired."""
    formed = [b for b, _ in _bearish_fvg_triple()]
    gaps = detect_fvgs(formed)
    assert len(gaps) == 1
    assert gaps[0].kind == "bearish"
    assert gaps[0].low == 22020
    assert gaps[0].high == 22050
    assert gaps[0].filled == "none"

    partial_bar, _ = _bar(3, 21990, 22030, 21980, 22010)  # high enters gap
    gaps = detect_fvgs(formed + [partial_bar])
    assert len(gaps) == 1 and gaps[0].filled == "partial"

    full_bar, _ = _bar(4, 22010, 22060, 22000, 22040)
    assert detect_fvgs(formed + [partial_bar, full_bar]) == []

    # Tight range: no new 3-bar gap, high stays below the original FVG top (no full fill).
    aged = formed + [_bar(3 + i, 21995, 22000, 21990, 21995)[0] for i in range(60)]
    assert detect_fvgs(aged) == []


def test_open_bar_never_forms_fvg():
    """An FVG whose third bar is still open is never reported."""
    first_two = [b for b, _ in _bullish_fvg_triple()[:2]]
    assert detect_fvgs(first_two) == []
    tracker = LocationTracker()
    for bar, ts in _bullish_fvg_triple()[:2]:
        tracker.on_bar(bar, ts)
    # Decision while the third minute is still open (before 09:18:01.5)
    now = datetime(2026, 1, 2, 9, 18, 0, tzinfo=IST)
    loc = tracker.snapshot(now, side="CE")
    assert loc is not None
    assert all(z["zone"] != "fvg" for z in loc.zones)


def test_candle_50_and_ema20_match_reference():
    """Candle 50% and EMA20 match the closed-bar references."""
    stamped = [_bar(i, 22000, 22010, 21990, 22000.0 + i) for i in range(25)]
    bars = [b for b, _ in stamped]
    loc = compute_entry_location(bars, side="CE")
    assert loc is not None
    mid = candle_50(bars[-1])
    assert mid is not None
    ema = EMA(period=20)
    for b in bars:
        assert b.c is not None
        ema.update(b.c)
    assert ema.value is not None
    by_zone = {z["zone"]: z for z in loc.zones}
    assert abs(float(by_zone["candle_50"]["price"]) - mid) < 1e-9
    assert abs(float(by_zone["ema20"]["price"]) - ema.value) < 1e-9
    assert abs(loc.signal_candle_atr - (bars[-1].h - bars[-1].l) / loc.atr) < 1e-9  # type: ignore[operator]


def test_vwap_futures_volume_or_twap_fallback():
    """VWAP uses futures volume when present; otherwise TWAP with the tag."""
    index_only = [_bar(i, 22000, 22010, 21990, 22000, v=None)[0] for i in range(5)]
    loc = compute_entry_location(index_only, side="CE")
    assert loc is not None
    vwap_zones = [z for z in loc.zones if z["zone"] == "vwap"]
    assert vwap_zones and all(z["source"] == "twap" for z in vwap_zones)

    fut = [
        _bar(
            i,
            22010,
            22020,
            22000,
            22010,
            instrument_id="NSE_FNO:NIFTY:2026-01-29",
            v=1000 + 100 * i,
        )[0]
        for i in range(5)
    ]
    loc_f = compute_entry_location(index_only, side="CE", fut_bars=fut)
    assert loc_f is not None
    sources = {z["source"] for z in loc_f.zones if z["zone"] == "vwap"}
    assert "fut_vwap" in sources and "twap" in sources


def test_poc_absent_without_futures_volume_matches_hand_profile():
    """POC is absent without futures volume; matches a hand-computed profile with it."""
    index = [_bar(i, 22000, 22010, 21990, 22000, v=None)[0] for i in range(3)]
    loc = compute_entry_location(index, side="CE")
    assert loc is not None
    assert all(z["zone"] != "poc" for z in loc.zones)

    # Hand profile: closes 22000 (v=10+20), 22010 (v=50) → POC 22010
    fut = [
        _bar(0, 22000, 22000, 22000, 22000, instrument_id="NSE_FNO:NIFTY:2026-01-29", v=10)[0],
        _bar(1, 22010, 22010, 22010, 22010, instrument_id="NSE_FNO:NIFTY:2026-01-29", v=50)[0],
        _bar(2, 22000, 22000, 22000, 22000, instrument_id="NSE_FNO:NIFTY:2026-01-29", v=20)[0],
    ]
    loc_p = compute_entry_location(index, side="CE", fut_bars=fut)
    assert loc_p is not None
    poc = next(z for z in loc_p.zones if z["zone"] == "poc")
    assert poc["price"] == 22010
    assert poc["source"] == "fut_volume_profile"


def test_distance_signs_ce_and_pe():
    """Positive distance_atr means stretched away from the pullback side."""
    bars = [b for b, _ in _bullish_fvg_triple()]
    # Close of last bar is 22060, FVG top 22040, candle 50% = 22065? last h=22090 l=22040 mid=22065
    loc_ce = compute_entry_location(bars, side="CE")
    loc_pe = compute_entry_location(bars, side="PE")
    assert loc_ce is not None and loc_pe is not None
    fvg_ce = next(z for z in loc_ce.zones if z["zone"] == "fvg")
    assert float(fvg_ce["distance_atr"]) > 0  # spot above FVG, CE stretched up
    assert abs(float(fvg_ce["distance_atr"]) - (22060 - 22040) / loc_ce.atr) < 1e-9
    # Same raw gap, PE flips the sign so + means stretched down (spot below a zone)
    assert signed_distance_atr(22060, 22040, loc_ce.atr, "CE") > 0
    assert signed_distance_atr(22060, 22040, loc_ce.atr, "PE") < 0
    pe_above = [z for z in loc_pe.zones if z["zone"] == "candle_50"]
    # last mid = (22090+22040)/2 = 22065 > spot 22060 → PE pullback side
    assert pe_above and float(pe_above[0]["distance_atr"]) > 0


def test_engine_entry_location_closed_bars_only():
    """FeatureEngine.entry_location uses only closed 1m bars (REG-01)."""
    engine = FeatureEngine()
    for bar, ts in _bullish_fvg_triple():
        engine.on_bar(bar, ts)
    now = datetime.fromisoformat(_bullish_fvg_triple()[-1][0].end) + timedelta(seconds=1.5)
    loc = engine.entry_location("NIFTY", "CE", now)
    assert loc is not None
    assert any(z["zone"] == "fvg" for z in loc.zones)
    early = datetime(2026, 1, 2, 9, 16, 30, tzinfo=IST)  # second bar still open
    loc_early = engine.entry_location("NIFTY", "CE", early)
    assert loc_early is None or all(z["zone"] != "fvg" for z in loc_early.zones)


def test_view_respects_requested_side():
    """loc_entry_distance_atr in view(side=) matches entry_location for that side."""
    engine = FeatureEngine()
    for bar, ts in _bullish_fvg_triple():
        engine.on_bar(bar, ts)
    now = datetime.fromisoformat(_bullish_fvg_triple()[-1][0].end) + timedelta(seconds=1.5)
    loc_ce = engine.entry_location("NIFTY", "CE", now)
    loc_pe = engine.entry_location("NIFTY", "PE", now)
    assert loc_ce is not None and loc_pe is not None
    ce = engine.view(now, side="CE").get("loc_entry_distance_atr", "NIFTY", "1m")
    pe = engine.view(now, side="PE").get("loc_entry_distance_atr", "NIFTY", "1m")
    if loc_ce.entry_distance_atr is not None:
        assert ce is not None
        assert abs(ce.value - loc_ce.entry_distance_atr) < 1e-9
    else:
        assert ce is None
    if loc_pe.entry_distance_atr is not None:
        assert pe is not None
        assert abs(pe.value - loc_pe.entry_distance_atr) < 1e-9
    else:
        assert pe is None


def test_tracker_mid_cut_equivalence():
    """Truncated tracker matches full tracker at the same t (REG-01b)."""
    stamped = _bullish_fvg_triple() + [
        _bar(3 + i, 22080, 22090, 22070, 22080) for i in range(20)
    ]
    full = LocationTracker()
    for bar, ts in stamped:
        full.on_bar(bar, ts)
    cut = 10
    now = stamped[cut][1]
    trunc = LocationTracker()
    for bar, ts in stamped:
        if ts <= now:
            trunc.on_bar(bar, ts)
    assert full.snapshot(now, side="CE") == trunc.snapshot(now, side="CE")
    assert full.feature_values(now, side="CE") == trunc.feature_values(now, side="CE")


def test_reset_session_clears_location():
    """reset_session drops location bars so yesterday's zones cannot leak."""
    engine = FeatureEngine()
    for bar, ts in _bullish_fvg_triple():
        engine.on_bar(bar, ts)
    now = datetime.fromisoformat(_bullish_fvg_triple()[-1][0].end) + timedelta(seconds=1.5)
    assert engine.entry_location("NIFTY", "CE", now) is not None
    engine.reset_session()
    assert engine.entry_location("NIFTY", "CE", now) is None
    assert engine.view(now).get("loc_spot", "NIFTY", "1m") is None
