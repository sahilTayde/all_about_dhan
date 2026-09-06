"""Smoke tests for agent_rag."""

from __future__ import annotations

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
    proposal = build_retune_proposal({"kind": "NORMAL", "flags": ["NORMAL"], "usable_for_retune_sample": True, "score_track": "SCORE_SAMPLE"})
    assert proposal["status"] == "BACKTEST_REQUIRED"
    assert proposal["backtest_results"] is None
