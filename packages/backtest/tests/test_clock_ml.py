from datetime import datetime, timedelta, timezone

from backtest_engine.clocks import drop_dead_band, in_founder_dead_band
from backtest_engine.indicators import Bar
from backtest_engine.ml_leans import lean_ml_logit
from backtest_engine.option_sim import simulate_option_premium


IST = timezone(timedelta(hours=5, minutes=30))


def _ts(h: int, m: int) -> int:
    return int(datetime(2026, 9, 1, h, m, tzinfo=IST).timestamp())


def test_dead_band_drops_preopen_and_cas():
    bars = [
        Bar(ts=_ts(9, 0), open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=_ts(9, 15), open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=_ts(9, 30), open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=_ts(9, 31), open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=_ts(14, 59), open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=_ts(15, 0), open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=_ts(15, 15), open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=_ts(15, 30), open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=_ts(15, 31), open=1, high=1, low=1, close=1, volume=1),
    ]
    assert in_founder_dead_band(_ts(9, 15))
    assert in_founder_dead_band(_ts(15, 15))
    assert not in_founder_dead_band(_ts(9, 31))
    assert not in_founder_dead_band(_ts(14, 59))
    kept = drop_dead_band(bars)
    mins = [(datetime.fromtimestamp(b.ts, tz=IST).hour, datetime.fromtimestamp(b.ts, tz=IST).minute) for b in kept]
    assert (9, 31) in mins
    assert (14, 59) in mins
    assert (9, 15) not in mins
    assert (15, 15) not in mins
    assert (15, 31) in mins


def test_session_end_flatten_exits_same_day():
    day = datetime(2026, 9, 1, 10, 0, tzinfo=IST)
    sig = [
        Bar(ts=int((day + timedelta(minutes=0)).timestamp()), open=100, high=101, low=99, close=100, volume=1),
        Bar(ts=int((day + timedelta(minutes=3)).timestamp()), open=100, high=101, low=99, close=101, volume=1),
    ]
    day2 = datetime(2026, 9, 2, 10, 0, tzinfo=IST)
    sig.append(
        Bar(ts=int(day2.timestamp()), open=100, high=101, low=99, close=100, volume=1)
    )
    leans = ["CE", "CE", "CE"]
    ce = [
        Bar(ts=sig[0].ts + 10, open=50, high=51, low=49, close=50, volume=1),
        Bar(ts=sig[1].ts + 10, open=52, high=53, low=51, close=52, volume=1),
        Bar(ts=sig[2].ts + 10, open=40, high=41, low=39, close=40, volume=1),
    ]
    trades = simulate_option_premium(
        sig,
        leans,
        ce,
        [],
        strategy_id="t",
        underlying="NIFTY",
        use_009=False,
        skip_open=False,
        session_end_flatten=True,
    )
    assert trades
    assert trades[0].reason == "session_end"


def test_ml_skips_before_train_end():
    bars = []
    px = 100.0
    t0 = _ts(10, 0)
    for i in range(80):
        px += 0.2
        bars.append(
            Bar(
                ts=t0 + i * 180,
                open=px,
                high=px + 0.5,
                low=px - 0.5,
                close=px,
                volume=1,
            )
        )
    cut = bars[40].ts
    leans = lean_ml_logit(bars, train_end_ts=cut)
    assert all(s == "SKIP" for s in leans[:40])
