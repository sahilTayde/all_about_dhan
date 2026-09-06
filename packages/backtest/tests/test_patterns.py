from backtest_engine.indicators import Bar
from backtest_engine.patterns import lean_donchian20, lean_mom_body, lean_orb_15


def test_mom_body():
    bars = [
        Bar(ts=1, open=10, high=12, low=9, close=11, volume=1),
        Bar(ts=2, open=11, high=12, low=8, close=9, volume=1),
    ]
    assert lean_mom_body(bars) == ["CE", "PE"]


def test_donchian_no_lookahead():
    bars = [
        Bar(ts=i, open=10, high=10, low=10, close=10, volume=1) for i in range(20)
    ]
    # Current bar high/close 20 would leak if the window included itself.
    bars.append(Bar(ts=20, open=10, high=20, low=10, close=20, volume=1))
    leans = lean_donchian20(bars)
    assert leans[19] == "SKIP"
    assert leans[20] == "CE"
    # Flat follow-up: close 15 is inside prior highs (max still 10 from bars 0-19
    # wait — after bar 20, window for i=21 is bars[1:21] whose high is 20.
    bars.append(Bar(ts=21, open=15, high=16, low=14, close=15, volume=1))
    leans = lean_donchian20(bars)
    assert leans[21] == "SKIP"


def test_orb_skips_before_930():
    # 09:15 IST on 2026-09-01 ≈ need timestamps in IST
    # 2026-09-01 09:15 IST = 2026-09-01 03:45 UTC = 1756698300 approx
    # Use clocks via known offset: IST = UTC+5:30
    from datetime import datetime, timedelta, timezone

    IST = timezone(timedelta(hours=5, minutes=30))
    day = datetime(2026, 9, 1, 9, 15, tzinfo=IST)
    bars_1m = []
    for m in range(20):
        ts = int((day + timedelta(minutes=m)).timestamp())
        bars_1m.append(Bar(ts=ts, open=100, high=101, low=99, close=100, volume=1))
    bars_1m[5] = Bar(ts=bars_1m[5].ts, open=100, high=110, low=99, close=105, volume=1)
    t930 = int(datetime(2026, 9, 1, 9, 33, tzinfo=IST).timestamp())
    bars_3m = [
        Bar(ts=int(datetime(2026, 9, 1, 9, 15, tzinfo=IST).timestamp()), open=100, high=101, low=99, close=100, volume=1),
        Bar(ts=t930, open=100, high=112, low=100, close=111, volume=1),
    ]
    leans = lean_orb_15(bars_1m, bars_3m)
    assert leans[0] == "SKIP"
    assert leans[1] == "CE"


def test_catalog_has_twenty_and_orb_skip_open_off():
    from backtest_engine.patterns import catalog_leans

    bars_3m = [
        Bar(ts=i, open=10, high=11, low=9, close=10, volume=1) for i in range(30)
    ]
    catalog = catalog_leans(bars_3m, bars_3m)
    assert len(catalog) == 20
    for orb_id in ("MIX-ORB-15", "MIX-ORB-VWAP", "MIX-CPR-ORB", "MIX-GAP"):
        assert catalog[orb_id][1] is False
    assert catalog["MIX-DONCHIAN-20"][1] is True
