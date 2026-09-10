"""INDEX 1m gather for paper detectors — no news, no orders."""

from __future__ import annotations

from trading_agents_india.hooks.index_bars import _to_bars, fetch_index_bars


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


