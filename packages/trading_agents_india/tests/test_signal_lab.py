"""Tests for signal_lab: resample, S/R, volume profile, edges, validation."""

from __future__ import annotations

from datetime import datetime

from trading_agents_india.premium_tape import IST, TapeBar
from trading_agents_india.signal_lab import (
    evaluate_combo,
    gate_series,
    opening_range,
    resample,
    summarize,
    volume_profile_poc,
)


def _ts(minute_offset: int) -> int:
    base = datetime(2026, 9, 9, 9, 15, tzinfo=IST)
    return int(base.timestamp()) + minute_offset * 60


def _bar(i: int, close: float, volume: float = 100.0, spread: float = 0.5) -> TapeBar:
    return TapeBar(
        ts=_ts(i),
        open=close - 0.1,
        high=close + spread,
        low=close - spread,
        close=close,
        volume=volume,
    )


def test_resample_3m_ohlcv() -> None:
    bars = [_bar(i, 100.0 + i, volume=10.0) for i in range(6)]
    out = resample(bars, 3)
    assert len(out) == 2
    first = out[0]
    assert first.open == bars[0].open
    assert first.close == bars[2].close
    assert first.high == max(b.high for b in bars[:3])
    assert first.low == min(b.low for b in bars[:3])
    assert first.volume == 30.0
    assert resample(bars, 1) == bars


def test_opening_range() -> None:
    bars = [_bar(i, 100.0 + (i % 3)) for i in range(20)]
    levels = opening_range(bars, minutes=15)
    assert levels is not None
    hi, lo = levels
    assert hi == max(b.high for b in bars[:15])
    assert lo == min(b.low for b in bars[:15])
    assert opening_range(bars[:10], minutes=15) is None


def test_volume_profile_poc_finds_heavy_node() -> None:
    bars = [_bar(i, 100.0, volume=1000.0) for i in range(30)]
    bars += [_bar(30 + i, 110.0, volume=1.0) for i in range(5)]
    poc = volume_profile_poc(bars)
    assert poc is not None and abs(poc - 100.0) < 2.0


def test_gate_series_mrr_vwap_rising_tape() -> None:
    bars = [_bar(i, 100.0 + 0.5 * i, volume=100.0 + i) for i in range(40)]
    gates = gate_series(bars, "mrr_vwap")
    assert len(gates) == 40
    assert gates[-1] is True
    assert not any(gates[:19])  # VWMA20 warmup


def test_evaluate_combo_rising_edge_and_forward() -> None:
    # Flat then rally: gate flips on once; entry is next 1m open.
    bars = [_bar(i, 100.0, volume=100.0) for i in range(25)]
    bars += [_bar(25 + i, 100.0 + 1.0 * (i + 1), volume=200.0) for i in range(60)]
    records = evaluate_combo(
        bars, day="2026-09-09", underlying="NIFTY", side="ce",
        timeframe=1, gate="mrr_vwap", overlay="none",
    )
    assert records, "expected at least one rising-edge signal"
    first = records[0]
    sig_idx = next(i for i, b in enumerate(bars) if b.ts == first.signal_ts)
    assert first.entry_price == round(bars[sig_idx + 1].open, 2)
    assert first.fwd["ret_15"] is not None and first.fwd["ret_15"] > 0
    # Rising edge: consecutive gate-on bars must not double-report.
    assert len(records) < 10


def test_overlay_vp_blocks_below_poc() -> None:
    # Heavy volume up top, price signals below POC -> vp overlay blocks all.
    bars = [_bar(i, 200.0, volume=5000.0) for i in range(20)]
    bars += [_bar(20 + i, 100.0 + 0.5 * i, volume=10.0) for i in range(50)]
    with_vp = evaluate_combo(
        bars, day="d", underlying="NIFTY", side="ce",
        timeframe=1, gate="mrr_vwap", overlay="vp",
    )
    without = evaluate_combo(
        bars, day="d", underlying="NIFTY", side="ce",
        timeframe=1, gate="mrr_vwap", overlay="none",
    )
    assert len(with_vp) < len(without) or (not with_vp and not without)


def test_pullback_gate_buys_dip_not_breakout() -> None:
    # Strong uptrend, then a dip toward EMA9: pullback fires on the dip.
    bars = [_bar(i, 100.0 + 1.0 * i, volume=100.0) for i in range(40)]
    bars += [_bar(40 + i, 139.0 - 1.5 * i, volume=100.0) for i in range(4)]  # dip
    bars += [_bar(44 + i, 134.0 + 1.0 * i, volume=100.0) for i in range(20)]
    gates = gate_series(bars, "pullback")
    assert any(gates[40:46]), "pullback should fire during the dip"
    assert not gates[39], "pullback must not fire at the breakout high"


def test_shell_outcome_stop_target_eod() -> None:
    from trading_agents_india.signal_lab import shell_outcome

    entry = 100.0
    # Target path: rallies 60% -> +50 (TP).
    up = [_bar(i, 100.0 + 4.0 * i) for i in range(20)]
    assert shell_outcome(up, 1, entry) == 50.0
    # Stop path: drops 30% -> -25 (SL).
    down = [_bar(i, 100.0 - 2.0 * i) for i in range(20)]
    assert shell_outcome(down, 1, entry) == -25.0
    # Flat path: EOD close exit near zero.
    flat = [_bar(i, 100.0, spread=0.1) for i in range(20)]
    out = shell_outcome(flat, 1, entry)
    assert out is not None and abs(out) < 1.0


def test_summarize_groups() -> None:
    bars = [_bar(i, 100.0, volume=100.0) for i in range(25)]
    bars += [_bar(25 + i, 101.0 + i, volume=200.0) for i in range(60)]
    records = []
    for tf in (1, 5):
        records += evaluate_combo(
            bars, day="d", underlying="NIFTY", side="ce",
            timeframe=tf, gate="mrr_vwap", overlay="none",
        )
    rows = summarize(records)
    assert {r["timeframe"] for r in rows} <= {1, 5}
    for row in rows:
        assert row["signals"] >= 1
        assert "avg_ret_pct_15m" in row
