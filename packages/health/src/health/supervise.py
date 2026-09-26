"""python -m health.supervise [options] -- <command...>

Keeps the live paper loop running. Restarts it with backoff when it exits non-zero (crash), and
kills and restarts it when its heartbeat (``engine_heartbeat.json``: ``last_loop_epoch``, written
at the top of every loop iteration) goes stale (hung). A clean exit (0: session over, founder stop
flag) ends supervision. launchd / systemd keep this supervisor alive (see ``deploy/``).

Each restart is appended to ``data/health/alerts.jsonl``. Never touches orders or brokers.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

log = logging.getLogger("health.supervise")
IST = timezone(timedelta(hours=5, minutes=30))
BACKOFF_SECONDS = (2.0, 5.0, 15.0, 60.0)


def last_beat(heartbeat: Path) -> Optional[float]:
    try:
        hb = json.loads(Path(heartbeat).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(hb, dict):
        return None
    stamps = [hb.get(k) for k in ("last_loop_epoch", "last_cycle_epoch")]
    vals = [float(v) for v in stamps if isinstance(v, (int, float))]
    return max(vals) if vals else None


def _alert(alerts: Optional[Path], message: str) -> None:
    log.error("%s", message)
    if alerts is None:
        return
    rec = {"ts": datetime.now(IST).isoformat(timespec="seconds"), "event": "ALERT", "check": "paper_engine",
           "severity": "CRITICAL", "error_kind": "supervisor_restart", "message": message}
    try:
        alerts.parent.mkdir(parents=True, exist_ok=True)
        with open(alerts, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass


def _stop(proc: subprocess.Popen, grace: float) -> None:
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def supervise(
    cmd: Sequence[str],
    *,
    heartbeat: Path,
    hang_seconds: float = 300.0,
    poll_seconds: float = 1.0,
    grace_seconds: float = 10.0,
    max_restarts: Optional[int] = None,
    alerts: Optional[Path] = None,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Returns the child's exit code once it exits cleanly, or 1 after ``max_restarts``."""
    restarts = 0
    while True:
        started = clock()
        proc = subprocess.Popen(list(cmd))
        outcome = ""
        while True:
            rc = proc.poll()
            if rc is not None:
                outcome = f"exited with code {rc}"
                break
            beat = last_beat(heartbeat)
            age = clock() - max(started, beat or 0.0)
            if age > hang_seconds:
                outcome = f"hung: no heartbeat for {age:.0f}s (limit {hang_seconds:.0f}s)"
                _stop(proc, grace_seconds)
                rc = proc.returncode if proc.returncode is not None else -9
                break
            sleep(poll_seconds)
        if outcome.startswith("exited") and rc == 0:
            return 0
        restarts += 1
        _alert(alerts, f"paper loop {outcome}; restart {restarts}")
        if max_restarts is not None and restarts > max_restarts:
            return 1
        sleep(BACKOFF_SECONDS[min(restarts - 1, len(BACKOFF_SECONDS) - 1)])


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        print("usage: python -m health.supervise [--heartbeat P] [--hang-seconds N] -- <command...>", file=sys.stderr)
        return 2
    split = argv.index("--")
    p = argparse.ArgumentParser(prog="python -m health.supervise")
    p.add_argument("--heartbeat", type=Path, default=Path("data/recon/engine_heartbeat.json"))
    p.add_argument("--alerts", type=Path, default=Path("data/health/alerts.jsonl"))
    p.add_argument("--hang-seconds", type=float, default=300.0)
    p.add_argument("--max-restarts", type=int, default=None)
    args = p.parse_args(argv[:split])
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    return supervise(argv[split + 1:], heartbeat=args.heartbeat, hang_seconds=args.hang_seconds,
                     max_restarts=args.max_restarts, alerts=args.alerts)


if __name__ == "__main__":
    sys.exit(main())
