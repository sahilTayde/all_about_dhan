"""health.supervise: restart a crashed loop, kill a hung one, stop on a clean exit, cap restarts."""

import json
import sys
import time

from health.supervise import DEFAULT_ALERTS, DEFAULT_HEARTBEAT, REPO, supervise

FAST = dict(poll_seconds=0.05, sleep=lambda s: time.sleep(min(s, 0.05)))


def _cmd(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def _alerts(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_clean_exit_ends_supervision(tmp_path):
    assert supervise(_cmd("raise SystemExit(0)"), heartbeat=tmp_path / "hb.json", alerts=tmp_path / "a", **FAST) == 0


def test_F1_market_closed_exit_code_2_is_clean_not_a_crash(tmp_path):
    """dual-tape exits 2 on weekends, before 09:30 and after 15:29 IST: no restart loop, no alert."""
    alerts = tmp_path / "alerts.jsonl"
    started = time.time()
    assert supervise(_cmd("raise SystemExit(2)"), heartbeat=tmp_path / "hb.json", alerts=alerts, **FAST) == 0
    assert time.time() - started < 5 and _alerts(alerts) == []


def test_crash_is_restarted_with_one_alert_per_incident(tmp_path):
    marker = tmp_path / "runs"
    code = (
        "import pathlib,sys; p=pathlib.Path(sys.argv[1]); n=int(p.read_text() or 0) if p.exists() else 0;"
        "p.write_text(str(n+1)); raise SystemExit(0 if n >= 3 else 3)"
    )
    alerts = tmp_path / "alerts.jsonl"
    rc = supervise([sys.executable, "-c", code, str(marker)], heartbeat=tmp_path / "hb.json", alerts=alerts, **FAST)
    assert rc == 0 and marker.read_text() == "4"  # three crashes, then a clean exit
    rows = _alerts(alerts)
    assert len(rows) == 1 and rows[0]["error_kind"] == "supervisor_restart" and "code 3" in rows[0]["message"]


def test_F1_restarts_are_capped(tmp_path):
    alerts = tmp_path / "alerts.jsonl"
    rc = supervise(_cmd("raise SystemExit(1)"), heartbeat=tmp_path / "hb.json", alerts=alerts, max_restarts=3, **FAST)
    assert rc == 1
    assert [r["error_kind"] for r in _alerts(alerts)] == ["supervisor_restart", "supervisor_gave_up"]


def test_hung_child_is_killed_and_restarted(tmp_path):
    alerts = tmp_path / "alerts.jsonl"
    started = time.time()
    rc = supervise(_cmd("import time; time.sleep(60)"), heartbeat=tmp_path / "hb.json", hang_seconds=0.5,
                   grace_seconds=1, max_restarts=1, alerts=alerts, **FAST)
    assert rc == 1 and time.time() - started < 20
    rows = _alerts(alerts)
    assert len(rows) == 2 and all("hung" in r["message"] for r in rows)


def test_beating_child_is_not_killed(tmp_path):
    hb = tmp_path / "hb.json"
    code = (
        "import json,time,sys; p=sys.argv[1]\n"
        "for _ in range(15):\n    open(p,'w').write(json.dumps({'last_loop_epoch': time.time()})); time.sleep(0.1)\n"
    )
    rc = supervise([sys.executable, "-c", code, str(hb)], heartbeat=hb, hang_seconds=1.0, max_restarts=0,
                   alerts=tmp_path / "a", **FAST)
    assert rc == 0


def test_default_paths_are_absolute_from_the_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert DEFAULT_HEARTBEAT.is_absolute() and DEFAULT_HEARTBEAT == REPO / "data" / "recon" / "engine_heartbeat.json"
    assert DEFAULT_ALERTS.is_absolute() and (REPO / "packages" / "health").is_dir()
