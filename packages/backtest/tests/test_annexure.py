from backtest_engine.algos import and_many
from backtest_engine.indicators import rsi
from backtest_engine.patterns import lean_rsi_mr


def test_rsi_flat_is_not_extreme():
    closes = [100.0 + (i % 3) * 0.1 for i in range(40)]
    r = rsi(closes, 14)
    assert r[14] is not None
    assert 0 <= r[14] <= 100


def test_rsi_mr_oversold_is_ce():
    # Sharp drop then low closes → RSI low
    closes = [100.0] * 15 + [80.0] * 10
    from backtest_engine.indicators import Bar

    bars = [
        Bar(ts=i, open=c, high=c, low=c, close=c, volume=1) for i, c in enumerate(closes)
    ]
    leans = lean_rsi_mr(bars, 30, 70)
    assert "CE" in leans


def test_and_many_requires_agreement():
    a = ["CE", "CE", "PE"]
    b = ["CE", "SKIP", "PE"]
    c = ["CE", "CE", "CE"]
    assert and_many([a, b, c]) == ["CE", "SKIP", "SKIP"]
