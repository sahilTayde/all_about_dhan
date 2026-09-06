from backtest_engine.indicators import Bar
from backtest_engine.option_sim import simulate_option_premium


def test_long_call_wins_when_premium_rises():
    sig = [
        Bar(ts=1_000, open=100, high=101, low=99, close=100, volume=1),
        Bar(ts=1_180, open=100, high=101, low=99, close=101, volume=1),
        Bar(ts=1_360, open=100, high=101, low=99, close=99, volume=1),
        Bar(ts=1_540, open=100, high=101, low=99, close=99, volume=1),
    ]
    leans = ["CE", "CE", "SKIP", "SKIP"]
    ce = [
        Bar(ts=1_050, open=50, high=51, low=49, close=50, volume=1),
        Bar(ts=1_200, open=52, high=60, low=52, close=59, volume=1),
        Bar(ts=1_400, open=58, high=58, low=40, close=41, volume=1),
    ]
    trades = simulate_option_premium(
        sig, leans, ce, [], strategy_id="t", underlying="NIFTY", use_009=False
    )
    assert trades
    assert trades[0].side == "CE"
    assert trades[0].points == trades[0].exit_px - trades[0].entry_px


def test_long_put_wins_when_premium_rises():
    sig = [
        Bar(ts=1_000, open=100, high=101, low=99, close=100, volume=1),
        Bar(ts=1_180, open=100, high=101, low=99, close=99, volume=1),
        Bar(ts=1_360, open=100, high=101, low=99, close=101, volume=1),
        Bar(ts=1_540, open=100, high=101, low=99, close=101, volume=1),
    ]
    leans = ["PE", "PE", "SKIP", "SKIP"]
    pe = [
        Bar(ts=1_050, open=40, high=41, low=39, close=40, volume=1),
        Bar(ts=1_200, open=45, high=50, low=45, close=49, volume=1),
        Bar(ts=1_400, open=48, high=48, low=30, close=31, volume=1),
    ]
    trades = simulate_option_premium(
        sig, leans, [], pe, strategy_id="t", underlying="NIFTY", use_009=False
    )
    assert trades
    assert trades[0].side == "PE"
    assert trades[0].points == trades[0].exit_px - trades[0].entry_px
    assert trades[0].points > 0
