"""Recorder health: a quiet tape is not HEALTHY."""

from __future__ import annotations

from pathlib import Path

from marketdata.status import STALE_AFTER_S, assess_health, write_status


def test_no_status_file_is_unhealthy(tmp_path: Path) -> None:
    report = assess_health(tmp_path, now=1_000_000.0, process_running=True)
    assert report["healthy"] is False
    assert report["verdict"] == "UNHEALTHY"
    assert "no frames" in report["reason"]


def test_recent_frame_is_healthy(tmp_path: Path) -> None:
    write_status(
        tmp_path,
        last_frame_ts="2026-10-11T10:00:00+05:30",
        last_frame_unix=1_000_000.0,
        frames=12,
        connected=True,
    )
    report = assess_health(tmp_path, now=1_000_010.0, process_running=True)
    assert report["healthy"] is True
    assert report["verdict"] == "HEALTHY"
    assert report["last_frame_age_s"] == 10.0


def test_stale_frame_is_unhealthy_even_if_process_up(tmp_path: Path) -> None:
    write_status(
        tmp_path,
        last_frame_ts="2026-10-11T10:00:00+05:30",
        last_frame_unix=1_000_000.0,
        frames=12,
        connected=True,
    )
    report = assess_health(tmp_path, now=1_000_000.0 + STALE_AFTER_S + 5.0, process_running=True)
    assert report["healthy"] is False
    assert "no frames in" in report["reason"]


def test_process_stopped_is_unhealthy(tmp_path: Path) -> None:
    write_status(
        tmp_path,
        last_frame_ts="2026-10-11T10:00:00+05:30",
        last_frame_unix=1_000_000.0,
        frames=3,
        connected=False,
    )
    report = assess_health(tmp_path, now=1_000_005.0, process_running=False)
    assert report["healthy"] is False
    assert "STOPPED" in report["reason"]
