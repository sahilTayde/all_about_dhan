"""Dual-tape loop: persist + founder stop + no orders."""

from __future__ import annotations

import json
from pathlib import Path

from trading_agents_india.config import Settings
from trading_agents_india.dual_tape import (
    STOP_FLAG_NAME,
    founder_stop_requested,
    run_dual_tape_loop,
)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        repo_root=tmp_path,
        kb_path=tmp_path / "tai_dual.sqlite",
        openai_model="unused",
        openai_key_present=False,
    )


def test_simulate_two_ticks_writes_ledger(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    result = run_dual_tape_loop(
        underlyings=["NIFTY"],
        tick_seconds=30,
        max_ticks=2,
        simulate=True,
        prefer_live_chain=False,
        persist=True,
        settings=settings,
        write_run_flag_on_start=False,
    )
    assert result.simulated is True
    assert result.tick_seconds == 30
    assert len(result.ticks) == 2
    assert "vol_watch" in result.ticks[0]
    assert result.stopped_reason == "completed_max_ticks"
    latest = tmp_path / "data" / "recon" / "paper_watch" / "DUAL-TAPE" / "latest.json"
    assert latest.is_file()
    notes = list((tmp_path / "data" / "recon" / "paper_watch" / "DUAL-TAPE").glob("*.notes.md"))
    assert notes
    overlay = tmp_path / "data" / "recon" / "paper_watch" / "DUAL-TAPE" / "overlay_last.json"
    assert overlay.is_file()
    blob = json.loads(overlay.read_text(encoding="utf-8"))
    assert blob["production_params_written"] is False
    assert blob["promote"] is False
    assert blob["session_action"] == "HOLD"
    text = notes[0].read_text(encoding="utf-8")
    assert "NIFTY" in text
    assert settings.kb_path.is_file()


def test_stop_flag_halts_before_tick(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    flag = tmp_path / "data" / "recon" / STOP_FLAG_NAME
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("stop\n", encoding="utf-8")
    assert founder_stop_requested(tmp_path)
    result = run_dual_tape_loop(
        underlyings=["NIFTY"],
        max_ticks=5,
        simulate=True,
        persist=False,
        settings=settings,
        write_run_flag_on_start=False,
    )
    assert result.stopped_reason == "founder_stop_flag"
    assert result.ticks == []
