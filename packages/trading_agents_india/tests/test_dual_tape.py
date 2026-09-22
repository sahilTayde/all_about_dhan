"""Dual-tape loop: persist + founder stop + no orders."""

from __future__ import annotations

import json
from datetime import datetime
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


def test_clamp_allows_10s_live_mock() -> None:
    from trading_agents_india.session_clock import clamp_tick_seconds

    assert clamp_tick_seconds(1) == 2
    assert clamp_tick_seconds(2) == 2
    assert clamp_tick_seconds(5) == 5
    assert clamp_tick_seconds(10) == 10
    assert clamp_tick_seconds(45) == 45


def test_carry_index_ltp() -> None:
    from trading_agents_india.dual_tape import _carry_index_ltp

    assert _carry_index_ltp({"index_ltp": 24850.5}) == 24850.5
    assert _carry_index_ltp({}) is None


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
    import sqlite3

    conn = sqlite3.connect(str(settings.kb_path))
    n = conn.execute("SELECT COUNT(*) FROM replay_index").fetchone()[0]
    assert n >= 1
    conn.close()


def test_jsonl_keeps_last_15_minutes(tmp_path: Path) -> None:
    from trading_agents_india.ledger import keep_jsonl_last_seconds
    from trading_agents_india.session_clock import IST, now_ist

    path = tmp_path / "tape.jsonl"
    now = int(now_ist().timestamp())
    rows = []
    for i in range(20):
        ts = now - (25 - i) * 60
        dt = datetime.fromtimestamp(ts, tz=IST)
        rows.append({"as_of_ist": dt.isoformat(timespec="seconds"), "i": i})
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    out = keep_jsonl_last_seconds(path, seconds=15 * 60, now_ts=now)
    assert out["ok"] is True
    kept = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert out["kept"] == len(kept)
    assert out["dropped"] >= 1
    assert all(now - 15 * 60 <= int(datetime.fromisoformat(r["as_of_ist"]).timestamp()) for r in kept)


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


def test_live_dual_tape_refuses_weekend(tmp_path: Path, monkeypatch) -> None:
    from datetime import datetime

    from trading_agents_india.session_clock import IST, WEEKEND_NO_MARKET

    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "trading_agents_india.dual_tape.now_ist",
        lambda override=None: datetime(2026, 9, 19, 12, 0, tzinfo=IST),
    )
    monkeypatch.setattr(
        "trading_agents_india.session_clock.now_ist",
        lambda override=None: override
        if override is not None
        else datetime(2026, 9, 19, 12, 0, tzinfo=IST),
    )
    result = run_dual_tape_loop(
        underlyings=["NIFTY"],
        max_ticks=3,
        simulate=False,
        persist=False,
        settings=settings,
        write_run_flag_on_start=False,
    )
    assert result.stopped_reason == WEEKEND_NO_MARKET
    assert result.ticks == []
