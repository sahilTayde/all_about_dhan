"""V2-15 service entry points + V2-19 llm-advisor sidecar.

Paper only. No broker calls. Tests inject ``state_dir`` — never write ``data/``.

V2-14 (PR #44) consumes ``breaker_open`` on a health snapshot. This module owns
the file and ``python -m runtime health`` / ``reset-breaker``. We do not import
``health.v2_*`` and do not start the V2-14 loopback ``/metrics`` server.
``python -m health`` stays the legacy PR-004 monitor. One compose health
process (this CLI). Protocol for the sibling: ``BreakerView.is_open``.

V2-19: ``LlmAdvisorService`` consumes ``boss:decisions`` and publishes ``ADVICE``
on ``llm:advice``. Weight 0: never waits in the engine, never vetoes, never
places an order. Replay uses ``RecordedProvider`` (no provider HTTP).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timedelta
from datetime import time as dt_time
from pathlib import Path
from typing import Any, Protocol

from contracts.clock import IST, Clock, LiveClock
from contracts.payloads import EngineStatus

log = logging.getLogger("runtime.services")
ADVICE_STREAM = "llm:advice"
DECISION_STREAM = "boss:decisions"
POSITION_STREAM = "pos:updates"

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
    """Compose READY contract: ENGINE_STATUS READY, no creds. Kernel does not change this."""
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


def _run_kernel_once(clock: Clock) -> None:
    """V2-04 kernel behind ``python -m runtime engine``. Empty tape when no source is wired."""
    from contracts.clock import SimClock
    from events.bus import MemoryBus

    from runtime.kernel import Engine
    from runtime.sources import EnvelopeSource
    from runtime.store import InMemoryLedgerStore

    sim = clock if isinstance(clock, SimClock) else SimClock(clock.now())
    Engine(EnvelopeSource([]), sim, MemoryBus(), [], InMemoryLedgerStore()).run()


def run_engine(state_dir: Path, clock: Clock | None = None, *, once: bool = False) -> None:
    clock = clock or LiveClock()
    write_engine_status(state_dir, clock)
    _run_kernel_once(clock)
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
    prev = state_dir.parent / (state_dir.name + ".backup_prev")
    if state_dir.exists():
        backup_state(state_dir, prev)
    sha_file = state_dir / "deployed_sha"
    current = sha_file.read_text(encoding="utf-8").strip() if sha_file.is_file() else ""
    state_dir.mkdir(parents=True, exist_ok=True)
    sha_file.write_text(sha + "\n", encoding="utf-8")
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


# ---------------------------------------------------------------------------
# V2-19 llm-advisor sidecar (off the engine path; advice only)
# ---------------------------------------------------------------------------


def _side_from_instrument(instrument_id: object) -> str | None:
    if not isinstance(instrument_id, str) or ":" not in instrument_id:
        return None
    tail = instrument_id.rsplit(":", 1)[-1].upper()
    return tail if tail in {"CE", "PE"} else None


class LlmAdvisorService:
    """Consume DECISION / POSITION_UPDATE; emit ADVICE. Never on the hot path."""

    def __init__(
        self,
        *,
        replay: bool,
        clock: Clock,
        cfg: Mapping[str, Any] | None = None,
        provider: Any = None,
        sink: Callable[[dict[str, Any]], None] | None = None,
        state_dir: Path | None = None,
    ) -> None:
        from desk_ml.llm_analyst import Advisor, load_config
        from desk_ml.llm_analyst.providers import RecordedProvider

        loaded = dict(cfg) if cfg is not None else load_config()
        loaded["weight"] = 0.0
        if state_dir is not None:
            loaded["log_path"] = str(state_dir / "llm_calls.jsonl")
            loaded["recorded_path"] = str(state_dir / "llm_recorded.jsonl")
            if loaded.get("replay_log_path"):
                loaded["replay_log_path"] = str(state_dir / "llm_replay.jsonl")
        if replay:
            loaded["replay_provider"] = "recorded"
        self.clock = clock
        self.replay = replay
        self.cfg = loaded
        self._sink = sink
        self._book: dict[str, Any] | None = None
        self.advisor = Advisor(loaded, replay=replay, provider=provider)
        if replay and provider is None and not isinstance(self.advisor.provider, RecordedProvider):
            self.advisor.provider = RecordedProvider(loaded)
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm-advisor")
        self._pending: list[Future[None]] = []

    def on_decision(self, decision: Mapping[str, Any]) -> None:
        """Fire-and-forget. Returns immediately. Never raises into the caller."""
        try:
            self._pending.append(self._pool.submit(self._review_and_publish, dict(decision)))
        except Exception:
            log.exception("llm-advisor submit failed")

    def on_position(self, update: Mapping[str, Any]) -> None:
        """Remember the last book snapshot for the next compact context."""
        try:
            qty = update.get("net_qty")
            self._book = {
                "open_positions": 1 if isinstance(qty, (int, float)) and qty else 0,
                "unrealized_inr": update.get("unrealized_inr"),
                "mark": update.get("mark"),
            }
        except Exception:
            log.exception("llm-advisor position snapshot failed")

    def consume(self, stream: str, payload: Mapping[str, Any]) -> None:
        if stream == DECISION_STREAM:
            self.on_decision(payload)
        elif stream == POSITION_STREAM:
            self.on_position(payload)

    def _context(self, decision: Mapping[str, Any]) -> dict[str, Any]:
        from desk_ml.llm_analyst import build_context

        now = self.clock.now()
        if now.tzinfo is None:
            raise ValueError("advisor clock must be IST-aware")
        raw_shadow = decision.get("shadow")
        shadow: Mapping[str, Any] = raw_shadow if isinstance(raw_shadow, Mapping) else {}
        regime = {"regime": shadow.get("regime")} if shadow.get("regime") else None
        return build_context(
            underlying=str(decision.get("underlying") or ""),
            tick_ts=int(now.timestamp()),
            ist_time=now.astimezone(IST).strftime("%H:%M"),
            signal={
                "side": _side_from_instrument(decision.get("instrument_id")),
                "confidence": 1.0 if decision.get("decision") == "ENTER" else 0.0,
            },
            regime=regime,
            book=self._book,
        )

    def _review_and_publish(self, decision: dict[str, Any]) -> None:
        from desk_ml.llm_analyst import PROMPT_VERSION

        try:
            out = self.advisor.review(self._context(decision))
            verdict = str(out.get("verdict") or "abstain")
            if verdict not in {"agree", "disagree", "abstain"}:
                verdict = "abstain"
            payload = {
                "decision_id": str(decision.get("decision_id") or ""),
                "verdict": verdict,
                "reasons": [str(r) for r in (out.get("reasons") or [])],
                "provider": str(self.advisor.provider.name),
                "prompt_version": str(PROMPT_VERSION),
                "cost_usd": float(out.get("cost_usd") or 0.0),
                "context_hash": str(out.get("context_hash") or ""),
            }
            if self._sink is not None:
                self._sink(payload)
        except Exception:
            log.exception("llm-advisor review failed (decision unchanged)")

    def wait_idle(self, timeout_s: float = 5.0) -> None:
        for fut in list(self._pending):
            with contextlib.suppress(Exception):
                fut.result(timeout=timeout_s)

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
        self.advisor.close()


def run_llm_advisor(
    state_dir: Path,
    clock: Clock | None = None,
    *,
    once: bool = True,
    replay: bool = True,
    service: LlmAdvisorService | None = None,
) -> LlmAdvisorService:
    """``python -m runtime llm-advisor``. Replay defaults to RecordedProvider. No broker."""
    clock = clock or LiveClock()
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "llm-advisor.ready").write_text("ok\n", encoding="utf-8")
    svc = service or LlmAdvisorService(replay=replay, clock=clock, state_dir=state_dir)
    if once:
        return svc
    while True:
        time.sleep(5)
