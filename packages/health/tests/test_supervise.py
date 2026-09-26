"""health.supervise: restart a crashed loop, kill and restart a hung one, stop on a clean exit."""

import json
import sys
import time

from health.supervise import supervise


def _cmd(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_clean_exit_ends_supervision(tmp_path):
    assert supervise(_cmd("raise SystemExit(0)"), heartbeat=tmp_path / "hb.json", poll_seconds=0.05,
                     sleep=lambda s: time.sleep(min(s, 0.05))) == 0


def test_crash_is_restarted_and_alerted(tmp_path):
    marker = tmp_path / "runs"
    code = (
        "import pathlib,sys; p=pathlib.Path(sys.argv[1]); n=int(p.read_text() or 0) if p.exists() else 0;"
        "p.write_text(str(n+1)); raise SystemExit(0 if n >= 1 else 3)"
    )
    alerts = tmp_path / "alerts.jsonl"
    rc = supervise([sys.executable, "-c", code, str(marker)], heartbeat=tmp_path / "hb.json", poll_seconds=0.05,
                   alerts=alerts, sleep=lambda s: time.sleep(min(s, 0.05)))
    assert rc == 0 and marker.read_text() == "2"
    rows = [json.loads(line) for line in alerts.read_text().splitlines()]
    assert len(rows) == 1 and "exited with code 3" in rows[0]["message"]


def test_hung_child_is_killed_and_restarted(tmp_path):
    hb = tmp_path / "hb.json"
    alerts = tmp_path / "alerts.jsonl"
    started = time.time()
    rc = supervise(_cmd("import time; time.sleep(60)"), heartbeat=hb, hang_seconds=0.5, poll_seconds=0.05,
                   grace_seconds=1, max_restarts=1, alerts=alerts, sleep=lambda s: time.sleep(min(s, 0.05)))
    assert rc == 1 and time.time() - started < 20
    rows = [json.loads(line) for line in alerts.read_text().splitlines()]
    assert len(rows) == 2 and all("hung" in r["message"] for r in rows)


def test_beating_child_is_not_killed(tmp_path):
    hb = tmp_path / "hb.json"
    code = (
        "import json,time,sys; p=sys.argv[1]\n"
        "for _ in range(15):\n    open(p,'w').write(json.dumps({'last_loop_epoch': time.time()})); time.sleep(0.1)\n"
    )
    rc = supervise([sys.executable, "-c", code, str(hb)], heartbeat=hb, hang_seconds=1.0, poll_seconds=0.05,
                   max_restarts=0, sleep=lambda s: time.sleep(min(s, 0.05)))
    assert rc == 0
