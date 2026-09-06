from backtest_engine.algos import mixed_index_veto, run_strat_003
from backtest_engine.indicators import Bar
from backtest_engine.live_signals import PaperSignalEngine
from backtest_engine.rating import rate_trades
from backtest_engine.simulate import Trade


def _trend(n: int, start: float, step: float, ts0: int = 1_725_000_000) -> list[Bar]:
    bars = []
    px = start
    for i in range(n):
        o = px
        px = px + step
        bars.append(
            Bar(
                ts=ts0 + i * 180,
                open=o,
                high=max(o, px) + 1,
                low=min(o, px) - 1,
                close=px,
                volume=1000,
            )
        )
    return bars


def test_uptrend_has_ce_trades():
    bars = _trend(80, 24000, 8)
    trades = run_strat_003(bars, underlying="NIFTY", use_007=False, use_009=False)
    assert trades
    assert any(t.side == "CE" for t in trades)


def test_mixed_index_veto():
    veto = mixed_index_veto(
        {
            "NIFTY": {"2026-09-01": "CE"},
            "BANKNIFTY": {"2026-09-01": "PE"},
            "SENSEX": {"2026-09-01": "CE"},
        }
    )
    assert "2026-09-01" in veto


def test_rating_insufficient():
    trades = [
        Trade(
            strategy_id="STRAT-003",
            underlying="NIFTY",
            side="CE",
            entry_ts=1,
            exit_ts=2,
            entry_px=1,
            exit_px=2,
            points=1,
            reason="x",
            session="2026-01-01",
        )
    ]
    r = rate_trades(trades, book_id="t")
    assert r["rating"] == "DATA_INSUFFICIENT"
    assert r["promote"] is False
    assert r["option_pnl"] is None


def test_and_same_side_and_align():
    from backtest_engine.algos import align_leans_to, and_same_side

    assert and_same_side(["CE", "CE", "PE"], ["CE", "SKIP", "PE"]) == ["CE", "SKIP", "PE"]
    src = [
        Bar(ts=100, open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=200, open=1, high=1, low=1, close=1, volume=1),
    ]
    tgt = [
        Bar(ts=150, open=1, high=1, low=1, close=1, volume=1),
        Bar(ts=250, open=1, high=1, low=1, close=1, volume=1),
    ]
    aligned = align_leans_to(tgt, src, ["CE", "PE"])
    assert aligned == ["CE", "PE"]


def test_paper_engine_hold_without_ticks():
    eng = PaperSignalEngine()
    snap = eng.snapshot()
    assert snap["orders"] == "refused"
    assert snap["research_ready_for_programming"] is False
