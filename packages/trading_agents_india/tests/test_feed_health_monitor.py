"""Ops monitor: Dhan feed death ≠ dealer deny."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "paper_ops_monitor", ROOT / "scripts" / "paper_ops_monitor.py"
)
assert SPEC and SPEC.loader
mon = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mon)


def _latest(*, index_ltp, index_delta, source, gaps, verdict):
    names = ("NIFTY", "BANKNIFTY", "SENSEX")
    return {
        "underlyings": [
            {
                "underlying": n,
                "index_ltp": index_ltp,
                "index_delta": index_delta,
                "index_source": source,
                "chain_source": "dhan_live" if "dhan" in source else "fixture",
                "premium_source": "dhan_rollingoption_1m" if "dhan" in source else "cache",
                "data_gaps": list(gaps),
            }
            for n in names
        ],
        "desk": [{"underlying": n, "verdict": verdict} for n in names],
    }


def test_dead_auth_is_not_deny():
    latest = _latest(
        index_ltp=None,
        index_delta=None,
        source="fixture",
        gaps=["DATA_INSUFFICIENT: dhan chain error DH-901 Invalid_Authentication"],
        verdict="DATA_INSUFFICIENT",
    )
    out = mon.classify_feed_health(latest=latest, in_session=True)
    assert out["class"] == "DEAD_AUTH"
    assert "not a dealer deny" in out["why"].lower() or "not a dealer deny day" in out["why"].lower()


def test_dead_api_null_index():
    latest = _latest(
        index_ltp=None,
        index_delta=None,
        source="simulate",
        gaps=["DATA_INSUFFICIENT: INDEX 1m DhanApiError"],
        verdict="DATA_INSUFFICIENT",
    )
    out = mon.classify_feed_health(latest=latest, in_session=True)
    assert out["class"] == "DEAD_API"
    assert "not 'all denied'" in out["why"] or "not a deny" in out["why"].lower()


def test_first_tick_live_ltp_no_delta():
    latest = _latest(
        index_ltp=23200.0,
        index_delta=None,
        source="dhan_intraday_1m",
        gaps=[],
        verdict="DATA_INSUFFICIENT",
    )
    out = mon.classify_feed_health(latest=latest, in_session=True)
    assert out["class"] == "FIRST_TICK"


def test_live_confirm_is_live():
    latest = _latest(
        index_ltp=23214.1,
        index_delta=6.3,
        source="dhan_intraday_1m",
        gaps=[],
        verdict="BUY_CE_CONFIRM",
    )
    out = mon.classify_feed_health(latest=latest, in_session=True)
    assert out["class"] == "LIVE"


def test_dealer_hold_not_feed_death():
    latest = _latest(
        index_ltp=56067.0,
        index_delta=26.8,
        source="dhan_intraday_1m",
        gaps=[],
        verdict="HOLD",
    )
    out = mon.classify_feed_health(latest=latest, in_session=True)
    assert out["class"] == "DEALER_HOLD"


def test_do_not_park_dhan_auth_attention():
    assert mon._is_parked_attention_why("DH-901 Invalid_Authentication feed death") is False
    assert mon._is_parked_attention_why("unbound STRAT DI ratio") is True


def test_notes_parser_does_not_split_on_tick_letter(tmp_path: Path):
    p = tmp_path / "notes.md"
    p.write_text(
        "## Tick 0 — 2026-09-16T09:15:08+05:30\n"
        "- **NIFTY** `DATA_INSUFFICIENT` / `DATA_INSUFFICIENT`: missing INDEX\n"
        "- **BANKNIFTY** `HOLD` / `STALE`: stale\n"
        "- **SENSEX** `BUY_CE_CONFIRM` / `CE_FOLLOWS`: confirm\n",
        encoding="utf-8",
    )
    stats = mon._count_live_dealer_notes(p)
    assert stats["live_ticks"] == 1
    assert stats["di"] == 1
    assert stats["hold"] == 1
    assert stats["confirm"] == 1


def test_ledger_counts_desk_dhan_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    day = tmp_path / "2026-09-16.jsonl"
    day.write_text(
        '{"event_type":"DESK_DIVERGENCE","verdict":"DATA_INSUFFICIENT","case":"DATA_INSUFFICIENT",'
        '"extra":{"data_gaps":["DATA_INSUFFICIENT: INDEX 1m DhanApiError"]}}\n'
        '{"event_type":"PAPER_TRADE","underlying":"NIFTY"}\n',
        encoding="utf-8",
    )
    out = mon._count_ledger(day)
    assert out["desk_divergence"] == 1
    assert out["desk_di"] == 1
    assert out["desk_dhan_api_error"] == 1
    assert out["paper_trade"] == 1
