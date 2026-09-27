"""V2-15 service entry points: restart breaker, stub engine, health, deploy.

Paper only. No broker calls. Tests inject ``state_dir`` — never write ``data/``.

V2-14 (PR #44) consumes ``breaker_open`` on a health snapshot. This module owns
the file and ``python -m runtime health`` / ``reset-breaker``. We do not import
``health.v2_*``. Protocol for the sibling: ``BreakerView.is_open``.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any, Protocol

from contracts.clock import IST, Clock, LiveClock
from contracts.payloads import EngineStatus

BREAKER_EXIT = 9
CRASH_LIMIT = 5
CRASH_WINDOW = timedelta(minutes=10)
BACKOFF_S = (1.0, 2.0, 4.0, 8.0, 16.0)
DEPLOY_BLOCK_START = dt_time(9, 0)
DEPLOY_BLOCK_END = dt_time(15, 35)
SERVICES = ("engine", "marketdata", "gateway", "health", "llm-advisor")


class BreakerView(Protocol):
    """Minimal V2-14 hook: snapshot.breaker_open = view.is_open()."""

    def is_open(self) -> bool: ...


class RestartBreaker:
    """REG-09: record starts in restarts.jsonl; open after 5 crashes / 10 min."""

    def __init__(self, state_dir: Path, service: str, clock: Clock) -> None:
        self.state_dir = state_dir
        self.service = service
        self.clock = clock
        self.path = state_dir / "restarts.jsonl"
        self.flag = state_dir / f"breaker_{service}.open"

    def _now(self) -> datetime:
        now = self.clock.now()
        if now.tzinfo is None:
            raise ValueError("breaker clock must be IST-aware")
        return now

    def _rows(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("service") == self.service:
                out.append(row)
        return out

    def _append(self, event: str) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": self._now().isoformat(timespec="seconds"),
            "service": self.service,
            "event": event,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")

    def crashes_in_window(self) -> int:
        now = self._now()
        n = 0
        for row in self._rows():
            if row.get("event") != "crash":
                continue
            ts = datetime.fromisoformat(str(row["ts"]))
            if now - ts <= CRASH_WINDOW:
                n += 1
        return n

    def is_open(self) -> bool:
        return self.flag.is_file()

    def record_start(self) -> None:
        self._append("start")

    def record_crash(self) -> bool:
        self._append("crash")
        if self.crashes_in_window() >= CRASH_LIMIT:
            self.flag.write_text(self._now().isoformat(timespec="seconds"), encoding="utf-8")
            self._append("open")
            return True
        return False

    def reset(self) -> None:
        if self.flag.exists():
            self.flag.unlink()
        self._append("reset")

    def backoff_s(self) -> float:
        n = max(0, self.crashes_in_window() - 1)
        return BACKOFF_S[min(n, len(BACKOFF_S) - 1)]


def run_guarded(
    service: str,
    fn: Callable[[], None],
    *,
    state_dir: Path,
    clock: Clock | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Entry-point wrapper: backoff on crash, exit BREAKER_EXIT when open."""
    clock = clock or LiveClock()
    br = RestartBreaker(state_dir, service, clock)
    if br.is_open():
        return BREAKER_EXIT
    br.record_start()
    try:
        fn()
        return 0
    except Exception:
        opened = br.record_crash()
        if opened:
            return BREAKER_EXIT
        sleep(br.backoff_s())
        return 1


def reset_breaker(service: str, state_dir: Path, clock: Clock | None = None) -> None:
    RestartBreaker(state_dir, service, clock or LiveClock()).reset()


def engine_status_path(state_dir: Path) -> Path:
    return state_dir / "engine_status.json"


def write_engine_status(state_dir: Path, clock: Clock, *, restart: bool = False) -> EngineStatus:
    """Stub engine (V2-04 kernel not on this branch): ENGINE_STATUS READY, no creds."""
    now = clock.now()
    session = now.astimezone(IST).date().isoformat()
    payload = EngineStatus(
        role="engine",
        status="READY",
        session=session,
        code_version=os.environ.get("AAD_SHA", "stub"),
        config_hash="paper-replay",
        basket_hash=None,
        restart=restart,
        input_lag_ms=0,
    )
    body = {**asdict(payload), "recon_ok": True, "ts": now.isoformat(timespec="seconds")}
    state_dir.mkdir(parents=True, exist_ok=True)
    engine_status_path(state_dir).write_text(json.dumps(body) + "\n", encoding="utf-8")
    return payload


def run_engine(state_dir: Path, clock: Clock | None = None, *, once: bool = False) -> None:
    clock = clock or LiveClock()
    write_engine_status(state_dir, clock)
    if once:
        return
    while True:
        time.sleep(5)
        write_engine_status(state_dir, clock)


def health_snapshot(state_dir: Path, clock: Clock) -> dict[str, Any]:
    """One health pass. V2-14 can copy ``breaker_open`` into its snapshot."""
    status_file = engine_status_path(state_dir)
    engine: dict[str, Any] = {}
    if status_file.is_file():
        engine = json.loads(status_file.read_text(encoding="utf-8"))
    snap = {
        "ts": clock.now().isoformat(timespec="seconds"),
        "engine_status": engine.get("status"),
        "recon_ok": engine.get("recon_ok"),
        "breaker_open": any(RestartBreaker(state_dir, name, clock).is_open() for name in SERVICES),
        "service": "health",
    }
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "health_status.json").write_text(json.dumps(snap) + "\n", encoding="utf-8")
    return snap


def run_health(state_dir: Path, clock: Clock | None = None, *, once: bool = True) -> dict[str, Any]:
    """``python -m runtime health`` — V2-15. Reads breaker file; does not import V2-14."""
    clock = clock or LiveClock()
    snap = health_snapshot(state_dir, clock)
    while not once:
        time.sleep(5)
        snap = health_snapshot(state_dir, clock)
    return snap


def in_market_deploy_window(now: datetime) -> bool:
    if now.tzinfo is None:
        raise ValueError("deploy clock must be IST-aware")
    t = now.astimezone(IST).time()
    return DEPLOY_BLOCK_START <= t <= DEPLOY_BLOCK_END


def wait_ready(state_dir: Path, *, timeout_s: float = 30.0, sleep: Callable[[float], None] = time.sleep) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        path = engine_status_path(state_dir)
        if path.is_file():
            body = json.loads(path.read_text(encoding="utf-8"))
            if body.get("status") == "READY" and body.get("recon_ok", True):
                return True
        sleep(0.05)
    return False


def output_hash(root: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "output_hash"):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def backup_state(state_dir: Path, dest: Path) -> str:
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(state_dir, dest)
    digest = output_hash(dest)
    (dest / "output_hash").write_text(digest + "\n", encoding="utf-8")
    return digest


def restore_state(snapshot: Path, state_dir: Path) -> str:
    expected = (snapshot / "output_hash").read_text(encoding="utf-8").strip()
    if state_dir.exists():
        shutil.rmtree(state_dir)
    shutil.copytree(snapshot, state_dir)
    got = output_hash(state_dir)
    if got != expected:
        raise RuntimeError("restore output hash mismatch")
    return got


def deploy(
    sha: str,
    *,
    state_dir: Path,
    clock: Clock,
    emergency: bool = False,
    ready_timeout_s: float = 5.0,
    start_engine: Callable[[], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Market-hours guard, backup, migrate stamp, health wait, auto-rollback."""
    now = clock.now()
    if in_market_deploy_window(now) and not emergency:
        return {"ok": False, "reason": "MARKET_HOURS", "ts": now.isoformat(timespec="seconds")}
    prev = state_dir / "backup_prev"
    if state_dir.exists():
        backup_state(state_dir, prev)
    current = (state_dir / "deployed_sha").read_text(encoding="utf-8").strip() if (state_dir / "deployed_sha").is_file() else ""
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "deployed_sha").write_text(sha + "\n", encoding="utf-8")
    (state_dir / "migrated").write_text("ok\n", encoding="utf-8")  # expand-only stub (V2-10)
    if start_engine is not None:
        start_engine()
    if wait_ready(state_dir, timeout_s=ready_timeout_s, sleep=sleep):
        return {"ok": True, "sha": sha, "ts": now.isoformat(timespec="seconds")}
    if prev.exists():
        restore_state(prev, state_dir)
    elif current:
        (state_dir / "deployed_sha").write_text(current + "\n", encoding="utf-8")
    return {"ok": False, "reason": "READY_TIMEOUT", "rolled_back": True, "sha": current or None}
