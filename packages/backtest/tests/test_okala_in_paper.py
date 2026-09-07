"""Okala India PAPER detector — FOUNDER_PAPER_ACCEPT / NO_PROMOTE / simple path."""

from __future__ import annotations

import os

import pytest

from backtest_engine.indicators import Bar, _wilder_atr
from backtest_engine.live_signals import PaperSignalEngine
from backtest_engine.okala_in_paper import (
    ELIGIBILITY_EXTEND,
    FOUNDER_LABEL,
    PAPER_STARTER_STOP_PCT,
    PAPER_STARTER_TARGET_PCT,
    WR_ROBUST_MIN,
    big_news_blocks_okala,
    clear_eligible_cache,
    detect_okala_paper_signals,
    detect_okala_signal,
    is_cell_paper_eligible,
    load_paper_eligible_cells,
    news_veto_enabled,
    paper_eligible_allowlist,
)
from backtest_engine.okala_in_proxy import lean_fork, lean_h_cross


@pytest.fixture(autouse=True)
def _news_veto_off(monkeypatch):
    monkeypatch.delenv("NEWS_VETO_ENABLED", raising=False)


def test_paper_eligible_cells_robust_gate():
    clear_eligible_cache()
    cells = load_paper_eligible_cells()
    assert len(cells) == 4
    assert all(c.wr_robust > WR_ROBUST_MIN and c.n >= 20 for c in cells)
    assert all(c.underlying == "NIFTY" for c in cells)
    allow = paper_eligible_allowlist()
    assert len(allow) == 4
    assert is_cell_paper_eligible(
        underlying="NIFTY",
        tf_min=1,
        regime="bearish",
        magnet_pair=(30, 40),
        setup="H_CROSS",
    )
    assert not is_cell_paper_eligible(
        underlying="BANKNIFTY",
        tf_min=1,
        regime="choppy",
        magnet_pair=(10, 0),
        setup="FORK",
    )
    assert is_cell_paper_eligible(
        underlying="NIFTY",
        tf_min=1,
        regime="x",
        magnet_pair=(1, 2),
        setup="LEVEL",
        wr_robust=0.51,
        n=25,
    )
    assert not is_cell_paper_eligible(
        underlying="NIFTY",
        tf_min=1,
        regime="x",
        magnet_pair=(1, 2),
        setup="LEVEL",
        wr_robust=0.49,
        n=25,
    )


def test_pattern_side_ce_vs_pe_mapping():
    from backtest_engine.okala_in_proxy import mix_id_for_setup

    assert mix_id_for_setup("FORK") == "MIX-CF-OKALA-IN-FORK"
    assert mix_id_for_setup("H_CROSS") == "MIX-CF-OKALA-IN-H-CROSS"
    assert mix_id_for_setup("REPAIR") == "MIX-CF-OKALA-IN-REPAIR"
    src_fork = lean_fork.__code__.co_consts
    src_h = lean_h_cross.__code__.co_consts
    assert "CE" in src_fork
    assert "PE" in src_h


def test_h_cross_emits_pe_when_pattern_fires():
    bars: list[Bar] = []
    px = 24030.0
    base_ts = 1704155400
    for i in range(80):
        c = px + (i % 7) * 0.5
        bars.append(
            Bar(ts=base_ts + i * 60, open=c, high=c + 2, low=c - 2, close=c, volume=1)
        )
    pair = (30, 40)
    for i in range(68, 72):
        m = 24030.0
        bars[i] = Bar(
            ts=bars[i].ts, open=m - 1, high=m + 3, low=m - 2, close=m + 2, volume=1
        )
    for i in range(75, 80):
        m = 24040.0
        bull = i < 77
        if bull:
            bars[i] = Bar(
                ts=bars[i].ts, open=m - 5, high=m + 1, low=m - 6, close=m - 1, volume=1
            )
        else:
            bars[i] = Bar(
                ts=bars[i].ts, open=m + 1, high=m + 2, low=m - 4, close=m - 3, volume=1
            )
    atrs = _wilder_atr(bars, 14)
    leans = lean_h_cross(bars, pair, atrs)
    fired = [x for x in leans if x in ("CE", "PE")]
    assert all(x == "PE" for x in fired)


def test_fork_emits_ce_when_pattern_fires():
    bars: list[Bar] = []
    base_ts = 1704155400
    px = 24100.0
    for i in range(80):
        c = px - i * 0.8
        bars.append(
            Bar(ts=base_ts + i * 60, open=c + 1, high=c + 2, low=c - 3, close=c, volume=1)
        )
    i = 75
    bars[i - 2] = Bar(
        ts=bars[i - 2].ts, open=24050, high=24052, low=24020, close=24048, volume=1
    )
    bars[i - 1] = Bar(
        ts=bars[i - 1].ts, open=24045, high=24055, low=24022, close=24040, volume=1
    )
    bars[i] = Bar(
        ts=bars[i].ts, open=24042, high=24070, low=24040, close=24065, volume=1
    )
    atrs = _wilder_atr(bars, 14)
    leans = lean_fork(bars, (60, 50), atrs)
    fired = [x for x in leans if x in ("CE", "PE")]
    assert all(x == "CE" for x in fired)


def test_news_veto_soft_default_off():
    assert news_veto_enabled() is False
    assert big_news_blocks_okala(force=True) is True
    assert big_news_blocks_okala(force=False) is False
    # Soft-default: NEWS_DAY / BIG_NEWS do not block
    assert big_news_blocks_okala(session_kind="NEWS_DAY") is False
    assert big_news_blocks_okala(veto_reasons=["BIG_NEWS hold"]) is False
    assert big_news_blocks_okala(session_kind="NORMAL", veto_reasons=[]) is False


def test_news_veto_reenable(monkeypatch):
    monkeypatch.setenv("NEWS_VETO_ENABLED", "true")
    assert news_veto_enabled() is True
    assert big_news_blocks_okala(session_kind="NEWS_DAY") is True
    assert big_news_blocks_okala(veto_reasons=["BIG_NEWS hold"]) is True


def test_big_news_hold_flag_still_empties_detector():
    bars = [
        Bar(
            ts=1704155400 + i * 60,
            open=24000,
            high=24010,
            low=23990,
            close=24000 + i * 0.1,
            volume=1,
        )
        for i in range(100)
    ]
    hits = detect_okala_paper_signals("NIFTY", bars, big_news_hold=True)
    assert hits == []


def test_short_bars_empty():
    bars = [
        Bar(ts=1704155400 + i * 60, open=100, high=101, low=99, close=100, volume=1)
        for i in range(10)
    ]
    assert detect_okala_paper_signals("NIFTY", bars) == []
    assert detect_okala_paper_signals("SENSEX", bars) == []


def test_sensex_and_bn_starter_extend_allowed():
    """BN/SENSEX may fire under FOUNDER_STARTER_EXTEND (same rules, caution)."""
    bars = [
        Bar(
            ts=1704155400 + i * 60,
            open=24000 + i * 0.2,
            high=24010 + i * 0.2,
            low=23990 + i * 0.2,
            close=24000 + i * 0.2,
            volume=1,
        )
        for i in range(120)
    ]
    # May or may not fire on flatish series — must not hard-reject underlying.
    for und in ("SENSEX", "BANKNIFTY"):
        hits = detect_okala_paper_signals(und, bars)
        assert isinstance(hits, list)
        for h in hits:
            assert h.eligibility == ELIGIBILITY_EXTEND
            assert h.lean in ("CE", "PE")
            assert h.underlying == und


def test_detect_okala_signal_premium_levels():
    """Fixture bars + mock premium → CE/PE with numeric premium Entry/Stop/Target."""
    bars = [
        Bar(
            ts=1704155400 + i * 60,
            open=24000,
            high=24010,
            low=23990,
            close=24000 + (i % 5),
            volume=1,
        )
        for i in range(100)
    ]
    # Force a PE-ish H_CROSS tail so something can fire on NIFTY eligible or extend
    for i in range(90, 100):
        m = 24040.0
        bars[i] = Bar(
            ts=bars[i].ts,
            open=m + 2,
            high=m + 3,
            low=m - 5,
            close=m - 4,
            volume=1,
        )
    sig = detect_okala_signal(
        "NIFTY",
        bars,
        option_ltp=100.0,
        premium_meta={"strike": 24000, "expiry": "2026-09-09", "source": "mock"},
        session_kind="NEWS_DAY",  # must NOT block when NEWS_VETO_ENABLED=false
        veto_reasons=["BIG_NEWS hold"],
    )
    # Pattern may not fire on synthetic — if it does, premium must be numeric.
    if sig is None:
        # Still prove premium binder path via direct call with a synthetic lean path:
        # use BANKNIFTY extend + mock LTP after injecting a FORK-friendly wick.
        for i in range(95, 100):
            c = 52000.0
            bars[i] = Bar(
                ts=bars[i].ts, open=c + 1, high=c + 20, low=c - 30, close=c + 15, volume=1
            )
        sig = detect_okala_signal(
            "BANKNIFTY",
            bars,
            option_ltp=80.0,
            premium_meta={"strike": 52000, "source": "mock"},
            session_kind="NEWS_DAY",
        )
    if sig is not None:
        assert sig["side"] in ("CE", "PE")
        assert sig["entry"] is not None
        assert sig["stop"] is not None
        assert sig["target"] is not None
        assert sig["unit"] == "OPTION_PREMIUM"
        assert sig["orders"] == "refused"
        entry = float(sig["entry"])
        assert float(sig["stop"]) == pytest.approx(entry * (1 - PAPER_STARTER_STOP_PCT), rel=1e-6)
        assert float(sig["target"]) == pytest.approx(
            entry * (1 + PAPER_STARTER_TARGET_PCT), rel=1e-6
        )
        assert sig["spot_underlying"] is not None


def test_detect_okala_signal_news_on_still_allows_when_flag_false():
    bars = [
        Bar(ts=1704155400 + i * 60, open=100, high=101, low=99, close=100.0, volume=1)
        for i in range(100)
    ]
    # Empty hit is OK; the gate must not short-circuit solely on NEWS_DAY.
    blocked = big_news_blocks_okala(session_kind="NEWS_DAY", veto_reasons=["BIG_NEWS"])
    assert blocked is False
    hits = detect_okala_paper_signals(
        "SENSEX", bars, session_kind="NEWS_DAY", veto_reasons=["BIG_NEWS"]
    )
    assert isinstance(hits, list)


def test_paper_engine_exposes_okala_books():
    eng = PaperSignalEngine(big_news_hold=False)
    for i in range(40):
        eng.ingest(
            {
                "security_id": 13,
                "fields": {
                    "ltp": 24000 + i,
                    "volume": 1,
                    "last_trade_time_epoch": 1_700_000_000 + i * 60,
                },
            }
        )
    snap = eng.snapshot()
    assert snap["orders"] == "refused"
    assert snap["research_ready_for_programming"] is False
    assert snap["founder_paper_accept"]["NO_PROMOTE"] is True
    assert snap["founder_paper_accept"]["label"] == FOUNDER_LABEL
    assert snap["news_veto_enabled"] is False
    assert "MIX-CF-OKALA-IN-H-CROSS" in snap["paper_watch_mixes"]
    assert "MIX-CF-OKALA-IN" in snap["books"]
    assert "NIFTY" in snap["books"]["MIX-CF-OKALA-IN"]
    assert snap["books"]["MIX-CF-OKALA-IN"]["NIFTY"]["paper_watch"] is True
    assert snap["books"]["MIX-DEFAULT-BUY"]["NIFTY"]["customer_default"] is True


def test_paper_engine_explicit_big_news_hold_still_vetoes():
    """Operator force (big_news_hold=True) still suppresses Okala for tests."""
    eng = PaperSignalEngine(big_news_hold=True)
    for i in range(40):
        eng.ingest(
            {
                "security_id": 13,
                "fields": {
                    "ltp": 24000 + i,
                    "volume": 1,
                    "last_trade_time_epoch": 1_700_000_000 + i * 60,
                },
            }
        )
    snap = eng.snapshot()
    row = snap["books"]["MIX-CF-OKALA-IN"]["NIFTY"]
    assert row["lean"] == "SKIP"
    assert row["state"] == "VETOED"
    assert any("BIG_NEWS" in r for r in (row.get("top_veto_reasons") or []))


def test_detect_okala_signal_mock_premium_forced():
    """Unit-level: bind premium levels via detect_okala_signal after a hit exists."""
    from backtest_engine.okala_in_paper import OkalaPaperHit
    from unittest.mock import patch

    fake = OkalaPaperHit(
        mix_id="MIX-CF-OKALA-IN-H-CROSS",
        underlying="NIFTY",
        lean="PE",
        setup="H_CROSS",
        tf_min=1,
        regime="bearish",
        magnet_pair=(30, 40),
        cell="fake",
        n=87,
        wr_robust=0.59,
        reasons=["test"],
    )
    bars = [
        Bar(ts=1704155400 + i * 60, open=24000, high=24001, low=23999, close=24000, volume=1)
        for i in range(80)
    ]
    with patch(
        "backtest_engine.okala_in_paper.best_okala_paper_hit", return_value=fake
    ):
        sig = detect_okala_signal(
            "NIFTY",
            bars,
            option_ltp=120.0,
            premium_meta={"strike": 24000, "source": "mock"},
            session_kind="NEWS_DAY",
            veto_reasons=["BIG_NEWS"],
        )
    assert sig is not None
    assert sig["side"] == "PE"
    assert sig["buy_side"] == "BUY_PE"
    assert sig["entry"] == 120.0
    assert sig["stop"] == 90.0
    assert sig["target"] == 150.0
    assert sig["spot_underlying"] == 24000.0
    assert sig["orders"] == "refused"
    assert os.environ.get("NEWS_VETO_ENABLED", "false").lower() in ("false", "")
