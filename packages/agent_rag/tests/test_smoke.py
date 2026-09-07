"""Smoke tests for agent_rag."""

from __future__ import annotations

import json
from pathlib import Path

from agent_rag.eod_recon import build_retune_proposal, run_eod_recon
from agent_rag.ingest import rebuild
from agent_rag.paths import agent_rag_db, repo_root, transcripts_db
from agent_rag.query import query


def test_rebuild_and_query_fake_breakout() -> None:
    root = repo_root()
    tdb = transcripts_db(root)
    tdb_mtime = tdb.stat().st_mtime if tdb.is_file() else None
    report = rebuild(root)
    assert report["doc_count"] > 10
    assert report["transcripts_sqlite_untouched"] is True
    assert agent_rag_db(root).is_file()
    if tdb_mtime is not None:
        assert tdb.stat().st_mtime == tdb_mtime
    hits = query("fake breakout", limit=5, root=root)
    # May be empty if phrase absent — still must not crash
    assert isinstance(hits, list)


def test_eod_recon_retune_required(tmp_path: Path | None = None) -> None:
    root = repo_root()
    out = run_eod_recon(
        day="2026-09-02",
        root=root,
        offline=True,
        update_continue=False,
    )
    assert out["retune_status"] == "BACKTEST_REQUIRED"
    assert out["promote"] is False
    assert out["keep_current_strategy"] is True
    assert out.get("tuned") is False
    proposal = build_retune_proposal(
        {
            "kind": "NORMAL",
            "flags": ["NORMAL"],
            "usable_for_retune_sample": True,
            "score_track": "SCORE_SAMPLE",
        }
    )
    assert proposal["status"] == "BACKTEST_REQUIRED"
    assert proposal["backtest_results"] is None
    assert proposal["tuned"] is False
    assert proposal["tune_status"] == "RAN_EMPTY_LEDGER"
    assert "done_when" in proposal


def test_eod_retune_proposal_extracts_observations(tmp_path: Path) -> None:
    """RAN_NO_TUNE with dig observations — not silent success / not a tune."""
    root = tmp_path
    day = "2099-01-03"
    ledger_dir = root / "data" / "recon" / "paper_ledger"
    ledger_dir.mkdir(parents=True)
    lines = [
        json.dumps(
            {
                "event_type": "SIGNAL",
                "underlying": "NIFTY",
                "lean": "HOLD",
                "stage": "VETOED",
                "risk_veto": True,
                "reasons": ["BIG_NEWS: hold"],
                "vetoes": ["BIG_NEWS: hold"],
                "data_gaps": ["OpenAI call failed (RateLimitError)"],
            }
        ),
        json.dumps(
            {
                "event_type": "CANDIDATE_OBSERVATION",
                "candidate_id": "STRAT-004",
                "outcome": "DATA_INSUFFICIENT",
                "data_gaps": [
                    "DATA_INSUFFICIENT: PAPER evaluator unbound "
                    "(PARKED/WAITING/NOT_CODED/overlay-incomplete); KEEP_ALL — not deleted"
                ],
                "provenance": {"candidate_evaluator_available": False},
            }
        ),
        json.dumps(
            {
                "event_type": "CANDIDATE_OBSERVATION",
                "candidate_id": "MIX-DEFAULT-BUY",
                "outcome": "VETOED",
                "data_gaps": [],
                "provenance": {"candidate_evaluator_available": True},
            }
        ),
    ]
    (ledger_dir / f"{day}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "data" / "recon").mkdir(parents=True, exist_ok=True)
    out = run_eod_recon(day=day, root=root, offline=True, update_continue=False)
    assert out["tune_status"] == "RAN_NO_TUNE"
    assert out["tuned"] is False
    assert out["production_params_written"] is False
    retune = json.loads(
        (root / "data" / "recon" / f"RETUNE_PROPOSAL_{day}.json").read_text(
            encoding="utf-8"
        )
    )
    assert retune["kind"] == "RETUNE_PROPOSAL"
    assert retune["status"] == "BACKTEST_REQUIRED"
    assert retune["tune_status"] == "RAN_NO_TUNE"
    assert retune["observations"]["news_severity_hits"].get("BIG_NEWS", 0) >= 1
    assert retune["observations"]["evaluator_available_false"] == 1
    assert retune["observations"]["evaluator_available_true"] == 1
    assert retune["done_when"]


def test_eod_reads_paper_ledger_jsonl(tmp_path: Path) -> None:
    """P0-3: paper_ledger/{day}.jsonl must set ledger.missing=false."""
    root = tmp_path
    day = "2099-01-02"
    ledger_dir = root / "data" / "recon" / "paper_ledger"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / f"{day}.jsonl").write_text(
        '{"event_type":"SIGNAL","underlying":"NIFTY","lean":"HOLD","stage":"VETOED","reasons":["BIG_NEWS: hold"]}\n',
        encoding="utf-8",
    )
    (root / "data" / "recon").mkdir(parents=True, exist_ok=True)
    (root / "teams" / "00_orchestrator" / "docs").mkdir(parents=True, exist_ok=True)
    out = run_eod_recon(day=day, root=root, offline=True, update_continue=False)
    payload = (root / "data" / "recon" / f"EOD_RECON_{day}.json").read_text(encoding="utf-8")
    import json

    blob = json.loads(payload)
    assert blob["ledger"]["missing"] is False
    assert blob["ledger"]["source"] == "paper_ledger_jsonl"
    assert blob["ledger"]["signal_count"] == 1
    assert out["promote"] is False
