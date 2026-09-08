"""INDEX 1m gather for paper detectors — no news, no orders."""

from __future__ import annotations

from trading_agents_india.hooks.index_bars import _to_bars, fetch_index_bars
from trading_agents_india.paper_evaluators import evaluate_candidate
from trading_agents_india.schemas import PaperTicket


def _ticket(**kwargs) -> PaperTicket:
    base = dict(
        underlying="NIFTY",
        lean="HOLD",
        stage="WATCH",
        reasons=["test"],
        risk_veto=False,
        vetoes=[],
        session_kind="NORMAL",
    )
    base.update(kwargs)
    return PaperTicket(**base)  # type: ignore[arg-type]


def test_to_bars_unwraps_data_and_pads_volume() -> None:
    payload = {
        "data": {
            "open": [1, 2],
            "high": [1.5, 2.5],
            "low": [0.5, 1.5],
            "close": [1.2, 2.2],
            "timestamp": [1, 2],
        }
    }
    bars = _to_bars(payload)
    assert len(bars) == 2
    assert float(bars[-1].close) == 2.2
    assert float(bars[0].volume) == 0.0


def test_fetch_index_bars_off_when_live_chain_off() -> None:
    result = fetch_index_bars("NIFTY", prefer_live=False)
    assert result.source == "unavailable"
    assert result.bar_count == 0
    assert any("live-chain off" in g for g in result.data_gaps)


def test_okala_watch_when_bars_present() -> None:
    from backtest_engine.indicators import Bar

    bars = [
        Bar(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100.5 + i, volume=0)
        for i in range(90)
    ]
    result = evaluate_candidate("MIX-CF-OKALA-IN-H-CROSS", _ticket(), bars=bars)
    assert result.available is True
    assert result.outcome != "DATA_INSUFFICIENT"
    assert not any("needs INDEX bars" in g for g in result.data_gaps)
