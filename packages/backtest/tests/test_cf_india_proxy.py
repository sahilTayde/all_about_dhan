"""Smoke tests for CF India sibling proxy (does not rewrite okala_in_proxy)."""

from __future__ import annotations

from backtest_engine.cf_india_proxy import india_decision, simulate_family
from backtest_engine.indicators import Bar


def _bars(n: int = 100) -> list[Bar]:
    base = 1704155400
    return [
        Bar(
            ts=base + i * 60,
            open=24000.0,
            high=24050.0,
            low=23950.0,
            close=24000.0 + (i % 40),
            volume=1.0,
        )
        for i in range(n)
    ]


def test_tori_skip_decision():
    # OpenAI overnight marked TORI as SKIP when suggest present
    d = india_decision("TORI")
    assert d in ("SKIP", "MISSING", "UNKNOWN", "PARTIAL")


def test_yush_probe_runs_or_skips():
    cell = simulate_family(_bars(), family="YUSH", underlying="NIFTY", tf_min=5)
    assert cell["family"] == "YUSH"
    assert cell.get("NO_PROMOTE") is True
    assert cell.get("win_rate_catalog") is None
    assert cell["status"] in ("RAN", "SKIP", "MISSING_OPENAI", "DATA_INSUFFICIENT")


def test_okala_proxy_untouched_import():
    # Sibling module must not redefine Okala magnet seed contract
    from backtest_engine import okala_in_proxy as o

    assert o.MAGNET_SEED == 20260907
    assert "LEVEL" in o.SETUPS
