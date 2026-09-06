from backtest_engine.indicators import Bar, all_three, bars_from_chart, session_vwap


def test_all_three_needs_warmup() -> None:
    bars = [
        Bar(ts=1_000_000 + i * 300, open=100, high=101, low=99, close=100.5, volume=10)
        for i in range(5)
    ]
    leans = all_three(bars)
    assert leans == ["SKIP"] * 5


def test_chart_parse() -> None:
    payload = {
        "open": [1, 2],
        "high": [1.5, 2.5],
        "low": [0.5, 1.5],
        "close": [1.2, 2.2],
        "volume": [10, 20],
        "timestamp": [1, 2],
    }
    bars = bars_from_chart(payload)
    assert len(bars) == 2
    vw = session_vwap(bars)
    assert vw[0] is not None
