from pathlib import Path

import pytest

from warehouse.feasibility import evaluate_long_premium
from warehouse.paths import assert_writable_db
from warehouse.store import Warehouse


def test_refuses_transcripts_db(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        assert_writable_db(tmp_path / "transcripts.sqlite")


def test_init_and_append(tmp_path: Path) -> None:
    db = tmp_path / "warehouse.sqlite"
    wh = Warehouse(db)
    assert wh.init()["schema_version"] == 3
    digest = wh.append_raw_event(
        source="fixture",
        symbol="NIFTY",
        segment="IDX",
        payload={"last": 1},
    )
    assert len(digest) == 64
    wh.append_bar(
        timeframe="1m",
        symbol="NIFTY",
        ts="2026-09-09T03:45:00+00:00",
        source="fixture",
        close=1.0,
    )
    wh.append_chain_snapshot(underlying="NIFTY", atm="25000", pcr=0.9)
    wh.append_features(
        symbol="NIFTY",
        ts="2026-09-09T03:45:00+00:00",
        feature_set_version="fs-0",
        features={"pcr": 0.9},
    )
    wh.upsert_signal(
        signal_id="paper-nifty-001",
        underlying="NIFTY",
        stage="WATCH",
        side="HOLD",
        levels={"entry": 150, "stop": 126, "target": 170},
        model_version="none",
        feature_set_version="fs-0",
    )
    wh.append_ticket_event(
        signal_id="paper-nifty-001",
        old_state="WATCH",
        new_state="WATCH",
        reason_code="OK",
    )
    wh.append_outcome(signal_id="paper-nifty-001", outcome="SHADOW_CLOSED", is_mock=True)
    wh.append_research_source(
        source_id="src-1",
        layer="HYPOTHESIS",
        digest="abc",
        title="test",
    )
    hashes = wh.append_counsel_event(
        job_id="SIGNAL_REVIEW",
        facts={"our_call": "HOLD"},
        prompt_version="v1",
        provider="both",
        model="gemini-3.5-flash-lite",
        verdict="HOLD",
        together="ALIGNED",
    )
    cached = wh.lookup_counsel(
        job_id="SIGNAL_REVIEW",
        facts={"our_call": "HOLD"},
        prompt_version="v1",
        model="gemini-3.5-flash-lite",
    )
    assert cached is not None
    assert cached["verdict"] == "HOLD"
    assert hashes["facts_hash"]
    status = wh.status()
    assert status["counts"]["signals"] == 1
    assert status["counts"]["counsel_events"] == 1


def test_founder_fantasy_target_holds_without_range() -> None:
    d = evaluate_long_premium(entry=150, stop=96, target=250, stage="WATCH")
    assert d.ok is False
    assert d.action == "HOLD"
    assert d.reason_code == "DATA_INSUFFICIENT"


def test_founder_fantasy_target_kills_with_range() -> None:
    d = evaluate_long_premium(
        entry=150,
        stop=96,
        target=250,
        typical_premium_range=20,
    )
    assert d.action == "KILL"
    assert d.reason_code == "TARGET_FEASIBILITY_FAIL"
    assert d.new_state == "FEASIBILITY_REJECTED"


def test_stop_above_entry_fails() -> None:
    d = evaluate_long_premium(entry=150, stop=160, target=170)
    assert d.reason_code == "STOP_FEASIBILITY_FAIL"


def test_stale_confirmed_kills() -> None:
    d = evaluate_long_premium(
        entry=150,
        stop=140,
        target=160,
        stage="CONFIRMED",
        tape_age_sec=999,
        typical_premium_range=30,
    )
    assert d.reason_code == "STALE_TAPE"
    assert d.new_state == "DEALER_KILLED"


def test_kill_priority() -> None:
    d = evaluate_long_premium(
        entry=150,
        stop=140,
        target=160,
        kill_requested=True,
        typical_premium_range=30,
    )
    assert d.action == "KILL"
    assert d.new_state == "DEALER_KILLED"


def test_ingest_oneshot_no_loop(tmp_path: Path) -> None:
    from types import SimpleNamespace

    from warehouse.ingest import ingest_once

    class Watch:
        source = "fixture"
        chain_lean = "NEUTRAL"
        spot = 23000.0
        atm_strike = 23000.0
        pcr_oi = 0.9
        atm_ce_ltp = None
        atm_pe_ltp = None
        expiry = "2026-09-15"

        def to_dict(self):
            return {"underlying": "NIFTY", "source": self.source, "chain_lean": "NEUTRAL"}

    class Index:
        source = "unavailable"
        bars = []
        bar_count = 0
        last_close = 23000.0

        def to_dict(self):
            return {"underlying": "NIFTY", "source": self.source, "bar_count": 0}

    score = SimpleNamespace(
        mix_id="MIX-LEAN-SPOT-ATM",
        lean="HOLD",
        stage="WATCH",
        entry=None,
        stop=None,
        target=None,
    )
    wh = Warehouse(tmp_path / "warehouse.sqlite")
    report = ingest_once(
        live=False,
        warehouse=wh,
        underlyings=("NIFTY",),
        sleep_s=0,
        watch_fn=lambda *_a, **_k: Watch(),
        bars_fn=lambda *_a, **_k: Index(),
        score_fn=lambda *_a, **_k: score,
    )
    assert report["loop_started"] is False
    assert report["orders"] == "refused"
    assert report["status"]["counts"]["signals"] == 1
    assert report["rows"][0]["NO_PROMOTE"] is True
