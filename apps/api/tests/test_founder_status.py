import json
import os
from datetime import datetime, timedelta, timezone

from api.founder_status import (
    PAPER_HEARTBEAT_STALE_S,
    _pid_alive,
    _scrub,
    build_founder_status,
    paper_loop_from_heartbeat,
)

_IST = timezone(timedelta(hours=5, minutes=30))
_THU_1030 = datetime(2026, 1, 15, 10, 30, tzinfo=_IST)
_THU_1600 = datetime(2026, 1, 15, 16, 0, tzinfo=_IST)


def test_scrub_drops_token_keys() -> None:
    out = _scrub({"access_token": "SECRET", "ok": True, "nested": {"dhan_access_token": "x"}})
    assert "access_token" not in out
    assert out["ok"] is True
    assert "dhan_access_token" not in out["nested"]


def test_build_founder_status_has_no_secret_strings() -> None:
    blob = build_founder_status()
    text = str(blob).lower()
    assert "eyj" not in text
    assert blob["orders"] == "REFUSED"
    assert blob["promote"] is False
    assert "agents" in blob
    assert "services" in blob
    assert blob.get("ml_paper", {}).get("win_rate") is None


def _alive(_pid: object) -> bool:
    return True


def _dead(_pid: object) -> bool:
    return False


def test_paper_loop_up_from_fresh_dual_tape_heartbeat() -> None:
    hb = {"pid": 4242, "last_loop_epoch": _THU_1030.timestamp() - 12, "consecutive_failures": 0}
    alive, pid, detail = paper_loop_from_heartbeat(hb, now=_THU_1030, pid_alive=_alive)
    assert alive is True
    assert pid == 4242
    assert "dual-tape heartbeat" in detail
    assert "last_loop" in detail


def test_paper_loop_down_on_empty_or_invalid_heartbeat() -> None:
    alive, pid, detail = paper_loop_from_heartbeat({}, now=_THU_1030, pid_alive=_alive)
    assert alive is False and pid is None and "no dual-tape heartbeat" in detail

    alive, pid, detail = paper_loop_from_heartbeat({"pid": 1}, now=_THU_1030, pid_alive=_alive)
    assert alive is False and "missing last_loop" in detail

    # last_loop present but pid missing — default os.kill check rejects pid None
    alive, pid, detail = paper_loop_from_heartbeat(
        {"last_loop_epoch": _THU_1030.timestamp()}, now=_THU_1030, pid_alive=_pid_alive
    )
    assert alive is False and pid is None and "pid not running" in detail


def test_paper_loop_down_when_heartbeat_pid_dead() -> None:
    hb = {"pid": 9, "last_loop_epoch": _THU_1030.timestamp() - 5}
    alive, pid, detail = paper_loop_from_heartbeat(hb, now=_THU_1030, pid_alive=_dead)
    assert alive is False
    assert pid is None
    assert "pid not running" in detail


def test_paper_loop_stale_heartbeat_during_market_hours() -> None:
    hb = {
        "pid": 7,
        "last_loop_epoch": _THU_1030.timestamp() - (PAPER_HEARTBEAT_STALE_S + 30),
        "last_loop_ist": "2026-01-15T10:27:00+05:30",
    }
    alive, pid, detail = paper_loop_from_heartbeat(hb, now=_THU_1030, pid_alive=_alive)
    assert alive is False
    assert pid == 7
    assert "stale" in detail


def test_paper_loop_stale_heartbeat_after_close_still_up_if_pid_alive() -> None:
    # Close leaves last_loop at ~15:29; do not false-DOWN the row after hours.
    hb = {"pid": 7, "last_loop_epoch": _THU_1600.timestamp() - 600}
    alive, pid, detail = paper_loop_from_heartbeat(hb, now=_THU_1600, pid_alive=_alive)
    assert alive is True
    assert pid == 7
    assert "dual-tape heartbeat" in detail


def test_paper_loop_accepts_last_loop_ist_without_epoch() -> None:
    hb = {"pid": 3, "last_loop_ist": "2026-01-15T10:29:40+05:30"}
    alive, pid, detail = paper_loop_from_heartbeat(hb, now=_THU_1030, pid_alive=_alive)
    assert alive is True
    assert pid == 3
    assert "dual-tape" in detail


def test_paper_loop_weekend_stale_heartbeat_up_if_pid_alive() -> None:
    sat = datetime(2026, 1, 17, 11, 0, tzinfo=_IST)  # Saturday
    hb = {"pid": 7, "last_loop_epoch": sat.timestamp() - 600}
    alive, pid, detail = paper_loop_from_heartbeat(hb, now=sat, pid_alive=_alive)
    assert alive is True and pid == 7
    assert "dual-tape heartbeat" in detail


def test_empty_heartbeat_file_is_not_up(tmp_path) -> None:
    from api.founder_status import _load_json

    path = tmp_path / "engine_heartbeat.json"
    path.write_text("", encoding="utf-8")
    alive, pid, detail = paper_loop_from_heartbeat(_load_json(path), now=_THU_1030, pid_alive=_alive)
    assert alive is False and pid is None
    assert "no dual-tape heartbeat" in detail

    path.write_text("{not json", encoding="utf-8")
    alive, _, detail = paper_loop_from_heartbeat(_load_json(path), now=_THU_1030, pid_alive=_alive)
    assert alive is False and "no dual-tape heartbeat" in detail


def test_build_founder_status_paper_up_from_heartbeat_file(tmp_path, monkeypatch) -> None:
    from api import founder_status as fs

    hb_path = tmp_path / "engine_heartbeat.json"
    now = datetime.now(fs._IST)
    hb_path.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "last_loop_epoch": now.timestamp(),
                "last_loop_ist": now.isoformat(timespec="seconds"),
                "consecutive_failures": 0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(fs, "_ENGINE_HB", hb_path)
    monkeypatch.setattr(fs, "_PIDS", tmp_path / "no-pids.json")
    monkeypatch.setattr(fs, "_STATUS", tmp_path / "no-status.json")
    monkeypatch.setattr(fs, "_STOP", tmp_path / "no-stop.flag")
    blob = fs.build_founder_status()
    paper = next(a for a in blob["agents"] if a["id"] == "paper-loop")
    assert paper["alive"] is True
    assert paper["pid"] == os.getpid()
    assert "dual-tape heartbeat" in paper["detail"]
    assert "Paper market-hours process is not running" not in blob["issues"]
    assert blob["orders"] == "REFUSED"
