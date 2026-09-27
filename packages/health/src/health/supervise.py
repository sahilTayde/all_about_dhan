"""python -m health.supervise [options] -- <command...>

Keeps the live paper loop running. Restarts it with backoff when it crashes, and kills and
restarts it when its heartbeat (``engine_heartbeat.json``: ``last_loop_epoch``, written at the top
of every loop iteration) goes stale (hung). A clean exit ends supervision: 0, and 2, which is how
dual-tape reports a closed market (weekend, before 09:30 IST, after 15:29 IST) or a usage error;
restarting those only spins. launchd / systemd start the supervisor each trading morning
(see ``deploy/``).

One incident = crashes/hangs with no healthy run in between. It gets one alert when it starts and
one if the supervisor gives up after ``max_restarts``. Alerts go to ``data/health/alerts.jsonl``.
Default paths are absolute from this repo, not the current folder. Never touches orders or brokers.
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
REPO = Path(__file__).resolve().parents[4]
DEFAULT_HEARTBEAT = REPO / "data" / "recon" / "engine_heartbeat.json"
DEFAULT_ALERTS = REPO / "data" / "health" / "alerts.jsonl"
CLEAN_EXIT_CODES = (0, 2)
BACKOFF_SECONDS = (5.0, 15.0, 60.0, 180.0, 600.0)
MAX_RESTARTS = 5
HEALTHY_AFTER_SECONDS = 600.0  # a run this long ends the incident; the next crash is a new one


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


def _alert(alerts: Optional[Path], message: str, kind: str) -> None:
    log.error("%s", message)
    if alerts is None:
        return
    rec = {"ts": datetime.now(IST).isoformat(timespec="seconds"), "event": "ALERT", "check": "paper_engine",
           "severity": "CRITICAL", "error_kind": kind, "message": message}
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
    heartbeat: Path = DEFAULT_HEARTBEAT,
    hang_seconds: float = 300.0,
    poll_seconds: float = 1.0,
    grace_seconds: float = 10.0,
    max_restarts: int = MAX_RESTARTS,
    clean_exit_codes: Sequence[int] = CLEAN_EXIT_CODES,
    healthy_after: float = HEALTHY_AFTER_SECONDS,
    alerts: Optional[Path] = DEFAULT_ALERTS,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """0 once the child exits cleanly; 1 after ``max_restarts`` restarts in one incident."""
    restarts = 0
    incident = 0
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
                rc = None
                break
            sleep(poll_seconds)
        if rc is not None and rc in clean_exit_codes:
            log.info("paper loop %s: clean exit (market closed, founder stop or done)", outcome)
            return 0
        if clock() - started >= healthy_after:
            restarts = 0  # it ran fine for a while: this failure starts a new incident
        restarts += 1
        if restarts == 1:
            incident += 1
            _alert(alerts, f"paper loop {outcome}; restarting with backoff (incident {incident})", "supervisor_restart")
        if restarts > max_restarts:
            _alert(alerts, f"paper loop {outcome}; gave up after {max_restarts} restarts (incident {incident})",
                   "supervisor_gave_up")
            return 1
        log.warning("paper loop %s; restart %d/%d", outcome, restarts, max_restarts)
        sleep(BACKOFF_SECONDS[min(restarts - 1, len(BACKOFF_SECONDS) - 1)])


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        print("usage: python -m health.supervise [--heartbeat P] [--hang-seconds N] -- <command...>", file=sys.stderr)
        return 2
    split = argv.index("--")
    p = argparse.ArgumentParser(prog="python -m health.supervise")
    p.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    p.add_argument("--alerts", type=Path, default=DEFAULT_ALERTS)
    p.add_argument("--hang-seconds", type=float, default=300.0)
    p.add_argument("--max-restarts", type=int, default=MAX_RESTARTS)
    args = p.parse_args(argv[:split])
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    return supervise(argv[split + 1:], heartbeat=args.heartbeat.resolve(), hang_seconds=args.hang_seconds,
                     max_restarts=args.max_restarts, alerts=args.alerts.resolve())


if __name__ == "__main__":
    sys.exit(main())
