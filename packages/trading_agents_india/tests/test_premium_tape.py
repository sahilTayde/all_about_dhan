"""Premium tape: parse, persist/load roundtrip, dual-master gate, scorer wiring."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from trading_agents_india import premium_tape
from trading_agents_india.premium_tape import (
    IST,
    TapeBar,
    _bars_from_side,
    dual_master_gate,
    load_tape_bars,
    persist_tape,
)
from trading_agents_india.lean_mix import score_dual_index_master
from trading_agents_india.schemas import PaperTicket

DAY = datetime(2026, 9, 10, tzinfo=IST)


def _ts(hour: int, minute: int) -> int:
    return int(DAY.replace(hour=hour, minute=minute).timestamp())


def _bull_bars(n: int = 40) -> list[TapeBar]:
    """Rising premium tape inside the 09:20-11:00 window, volume spike on last bar."""
    bars = []
    base = 100.0
    for i in range(n):
        px = base + i * 1.5
        bars.append(
            TapeBar(
                ts=_ts(9, 20 + i),
                open=px,
                high=px + 1.2,
                low=px - 0.4,
                close=px + 1.0,
                volume=1000.0 if i < n - 1 else 5000.0,
            )
        )
    return bars


def _payload() -> dict:
    ts = [_ts(9, 20 + i) for i in range(3)]
    side = {
        "open": [100.0, 101.0, 102.0],
        "high": [101.0, 102.0, 103.0],
        "low": [99.5, 100.5, 101.5],
        "close": [100.8, 101.8, 102.8],
        "volume": [500, 600, 700],
        "timestamp": ts,
    }
    return {"data": {"ce": side, "pe": dict(side)}}


def test_parse_ce_and_pe_sides() -> None:
    ce = _bars_from_side(_payload(), "ce")
    pe = _bars_from_side(_payload(), "pe")
    assert len(ce) == 3 and len(pe) == 3
    assert ce[0].close == 100.8


def test_persist_and_load_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(premium_tape, "tape_dir", lambda: tmp_path)
    ce = _bars_from_side(_payload(), "ce")
    days = persist_tape("SENSEX", ce=ce, pe=[], source="test")
    assert days == ["2026-09-10"]
    loaded = load_tape_bars("SENSEX", day="2026-09-10", side="ce")
    assert [b.ts for b in loaded] == [b.ts for b in ce]
    # Upsert merge: re-persist overlapping + one new bar.
    extra = TapeBar(ts=_ts(9, 23), open=103.0, high=104.0, low=102.5, close=103.8, volume=800)
    persist_tape("SENSEX", ce=[ce[-1], extra], pe=[], source="test")
    merged = load_tape_bars("SENSEX", day="2026-09-10", side="ce")
    assert len(merged) == 4
    blob = json.loads((tmp_path / "SENSEX_ATM_1m_2026-09-10.json").read_text())
    assert blob["meta"]["strike"] == "ATM"


def test_gate_needs_min_bars() -> None:
    out = dual_master_gate(_bull_bars(10))
    assert out["evaluated"] is False


def test_gate_all_pass_on_bull_tape() -> None:
    out = dual_master_gate(_bull_bars(40))
    assert out["evaluated"] is True
    assert out["all_pass"] is True
    assert out["conditions"]["volume_spike"] is True
    assert out["conditions"]["in_time_window"] is True


def test_gate_fails_outside_window() -> None:
    bars = _bull_bars(40)
    shifted = [
        TapeBar(
            ts=_ts(11, 30) + i * 60,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume,
        )
        for i, b in enumerate(bars)
    ]
    out = dual_master_gate(shifted)
    assert out["evaluated"] is True
    assert out["all_pass"] is False
    assert out["conditions"]["in_time_window"] is False


def _spot_bars(n: int = 30):
    from backtest_engine.indicators import Bar

    return [
        Bar(
            ts=_ts(9, 20 + i),
            open=81000.0 + i * 10,
            high=81010.0 + i * 10,
            low=80990.0 + i * 10,
            close=81005.0 + i * 10,
            volume=0,
        )
        for i in range(n)
    ]


def _ticket(**kwargs) -> PaperTicket:
    base = dict(
        underlying="SENSEX",
        lean="HOLD",
        stage="WATCH",
        reasons=["gather"],
        risk_veto=False,
        vetoes=[],
        session_kind="NORMAL",
        premium_lean={"source": "optionchain_atm", "option_ltp": 150.0},
    )
    base.update(kwargs)
    return PaperTicket(**base)  # type: ignore[arg-type]


def test_scorer_buy_ce_watch_when_both_gates_pass() -> None:
    hit = score_dual_index_master(_ticket(), bars=_spot_bars(), premium_bars=_bull_bars(40))
    assert hit.lean == "BUY_CE"
    assert hit.stage == "WATCH"
    assert hit.outcome == "WATCH"
    assert hit.provenance["NO_PROMOTE"] is True
    assert hit.provenance["premium_gate"]["all_pass"] is True
    assert not any("premium OHLC" in g for g in hit.data_gaps)


def test_scorer_holds_when_premium_gate_fails() -> None:
    bars = _bull_bars(40)
    weak = bars[:-1] + [
        TapeBar(
            ts=bars[-1].ts,
            open=bars[-1].open,
            high=bars[-1].high,
            low=bars[-1].low,
            close=bars[-1].close,
            volume=100.0,  # no volume spike
        )
    ]
    hit = score_dual_index_master(_ticket(), bars=_spot_bars(), premium_bars=weak)
    assert hit.lean == "HOLD"
    assert "volume_spike" in " ".join(hit.reasons)


def test_scorer_keeps_blocker_without_tape() -> None:
    hit = score_dual_index_master(_ticket(), bars=_spot_bars(), premium_bars=None)
    assert hit.lean == "HOLD"
    assert any("CALL premium OHLC" in g for g in hit.data_gaps)


def test_strike_label_paths_and_validation(tmp_path, monkeypatch) -> None:
    from trading_agents_india.premium_tape import _tape_path, gather_premium_tape

    monkeypatch.setattr(premium_tape, "tape_dir", lambda: tmp_path)
    assert _tape_path("NIFTY", "2026-09-11", "ATM+1").name == "NIFTY_ATMp1_1m_2026-09-11.json"
    assert _tape_path("NIFTY", "2026-09-11", "ATM-2").name == "NIFTY_ATMm2_1m_2026-09-11.json"
    # Unknown labels refused (Dhan silently falls back to ATM on bad labels).
    res = gather_premium_tape("NIFTY", prefer_live=True, strike_label="OTM9")
    assert res.source == "unavailable"
    assert any("refused" in g for g in res.data_gaps)
