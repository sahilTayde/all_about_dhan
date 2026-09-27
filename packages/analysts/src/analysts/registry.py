"""Analyst registry (config key -> factory) and the room that runs them with a per-analyst timeout.

New analyst / research feature:

    from analysts import Analyst, Vote, register

    @register("MY-FEATURE")
    class MyFeature(Analyst):
        analyst_id = "MY-FEATURE"
        def vote(self, ctx): ...

then add "MY-FEATURE" to `analysts:` in config/analysts.yaml. An enabled analyst votes in the
picker majority like any other. Crash or timeout = ABSTAIN; the boss never sees the exception.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, wait
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import yaml

from analysts.base import Analyst, MarketContext, Vote

log = logging.getLogger("analysts")

REGISTRY: dict[str, Callable[[], Analyst]] = {}
DEFAULT_TIMEOUT_S = 0.5


def register(key: str, factory: Optional[Callable[[], Analyst]] = None) -> Any:
    """`register("KEY", factory)` or `@register("KEY")` on an Analyst subclass."""

    def _add(f: Callable[[], Analyst]) -> Callable[[], Analyst]:
        if key in REGISTRY:
            raise ValueError(f"analyst key {key!r} already registered")
        REGISTRY[key] = f
        return f

    return _add(factory) if factory is not None else _add


def default_keys() -> list[str]:
    from analysts.legacy import LEGACY_SOURCES

    return list(LEGACY_SOURCES)


def build(keys: Optional[Sequence[str]] = None) -> list[Analyst]:
    import analysts.legacy  # noqa: F401  (registers the paper engine's room)
    import analysts.shadow  # noqa: F401  (shadow analysts; boss ignores them)
    import analysts.llm  # noqa: F401  (PR-016 LLM-ANALYST; advisory, weight 0 = shadow)

    wanted = list(keys) if keys is not None else default_keys()
    unknown = [k for k in wanted if k not in REGISTRY]
    if unknown:
        raise ValueError(f"unknown analyst keys {unknown}; registered: {sorted(REGISTRY)}")
    out: list[Analyst] = []
    for key in wanted:
        try:
            out.append(REGISTRY[key]())
        except Exception as exc:
            # A broken analyst (bad yaml, import error) is dropped. The rest of the room still votes.
            log.error("analyst %s failed to start (%s: %s); disabled", key, type(exc).__name__, exc)
    return out


def _parse_analyst_entry(item: Any) -> tuple[str, bool, Optional[int]]:
    """A yaml string, or ``{key, shadow, timeout_ms}``. Returns (key, shadow, timeout_ms or None)."""
    if isinstance(item, str):
        return item, False, None
    if isinstance(item, dict):
        key = item.get("key") or item.get("id")
        if not key:
            raise ValueError(f"analyst entry missing key: {item}")
        timeout = item.get("timeout_ms")
        return str(key), bool(item.get("shadow")), (int(timeout) if timeout is not None else None)
    return str(item), False, None


def load_config(path: Optional[Path] = None) -> dict[str, Any]:
    """config/analysts.yaml.

    ``analysts`` is every enabled key in order. ``voting`` omits ``shadow: true`` rows
    (those still run and are audited; the boss ignores them). ``timeout_ms`` is the
    default per-analyst wall-clock budget; ``timeouts_ms`` overrides one key.
    Missing file = the paper room, 500 ms, no shadows.
    """
    cfg: dict[str, Any] = {}
    if path is not None and Path(path).is_file():
        cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    raw = cfg.get("analysts") or default_keys()
    keys: list[str] = []
    shadow: list[str] = []
    timeouts: dict[str, int] = {}
    for item in raw:
        key, is_shadow, timeout = _parse_analyst_entry(item)
        keys.append(key)
        if is_shadow:
            shadow.append(key)
        if timeout is not None:
            timeouts[key] = timeout
    shadow_set = set(shadow)
    return {
        "analysts": keys,
        "voting": [k for k in keys if k not in shadow_set],
        "shadow": shadow,
        "timeout_ms": int(cfg.get("timeout_ms") or DEFAULT_TIMEOUT_S * 1000),
        "timeouts_ms": timeouts,
        "shadow_cfg": {"features": cfg.get("features") or {}, "shadow": cfg.get("shadow") or {}},
    }


class AnalystRoom:
    """Runs every analyst on a context in parallel; each gets `timeout_s` from the request.

    ponytail: Python threads cannot be killed, so a hung analyst keeps its worker; the room has
    one worker per analyst, so one hang costs that analyst's slot only. Upgrade to a process pool
    if an analyst ever wraps blocking I/O.
    """

    def __init__(
        self,
        analysts: Sequence[Analyst],
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        timeouts_s: Optional[dict[str, float]] = None,
        shadow_ids: Optional[Sequence[str]] = None,
        shadow_cfg: Optional[dict[str, Any]] = None,
        deterministic: bool = False,
        live_loop: bool = False,
    ) -> None:
        ids = [a.analyst_id for a in analysts]
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate analyst ids {ids}")
        self.analysts = list(analysts)
        self.timeout_s = float(timeout_s)
        self.timeouts_s = {str(k): float(v) for k, v in (timeouts_s or {}).items()}
        self.shadow_ids = set(shadow_ids or [])
        self.shadow_cfg = dict(shadow_cfg or {})
        # Replay/parity must not ABSTAIN the voting room because the machine was busy.
        # Analysts that block (the LLM, `wall_clock`) still get a hard cap so one hang cannot stall a replay.
        self.deterministic = bool(deterministic)
        # Online LLM only while the live paper loop is running. live_session replays stay offline.
        self.live_loop = bool(live_loop)
        for a in self.analysts:
            if hasattr(a, "set_replay"):
                a.set_replay(not self.live_loop)
        self._pool = None if self.deterministic else ThreadPoolExecutor(
            max_workers=max(1, len(self.analysts)), thread_name_prefix="analyst"
        )
        self._cap_pool: Optional[ThreadPoolExecutor] = None
        self._inflight: dict[str, Any] = {}
        self.stats = {"votes": 0, "timeouts": 0, "errors": 0}

    @classmethod
    def from_config(cls, path: Optional[Path] = None, *, deterministic: bool = False, live_loop: bool = False) -> "AnalystRoom":
        try:
            cfg = load_config(path)
            analysts = build(cfg["analysts"])
        except Exception as exc:
            log.exception("analyst config %s failed (%s); using the default paper room", path, exc)
            return cls(build(default_keys()), timeout_s=DEFAULT_TIMEOUT_S, deterministic=deterministic, live_loop=live_loop)
        return cls(
            analysts,
            timeout_s=cfg["timeout_ms"] / 1000.0,
            timeouts_s={k: v / 1000.0 for k, v in cfg["timeouts_ms"].items()},
            shadow_ids=cfg["shadow"],
            shadow_cfg=cfg["shadow_cfg"],
            deterministic=deterministic,
            live_loop=live_loop,
        )

    def timeout_for(self, analyst: Analyst) -> float:
        return float(self.timeouts_s.get(analyst.analyst_id, self.timeout_s))

    @property
    def analyst_ids(self) -> list[str]:
        return [a.analyst_id for a in self.analysts]

    def _run(self, analyst: Analyst, ctx: MarketContext) -> Vote:
        vote = analyst.vote(ctx)
        if not isinstance(vote, Vote) or vote.analyst_id != analyst.analyst_id:
            raise TypeError(f"{analyst.analyst_id} returned {vote!r}, not its own Vote")
        return vote

    def _take(self, analyst: Analyst, fut: Any, ms: float) -> tuple[Vote, float]:
        exc = fut.exception()
        if exc is not None:
            self.stats["errors"] += 1
            log.warning("analyst %s crashed (%s: %s) -> ABSTAIN", analyst.analyst_id, type(exc).__name__, exc)
            return Vote.abstain(analyst.analyst_id, f"ERROR:{type(exc).__name__}"), ms
        return fut.result(), ms

    def _replay_capped(self, analyst: Analyst) -> bool:
        """Per-key timeout_ms, or an analyst that can block (the LLM). Voting analysts stay inline."""
        return analyst.analyst_id in self.timeouts_s or bool(getattr(analyst, "wall_clock", False))

    def _run_capped(self, analyst: Analyst, ctx: MarketContext, limit: float) -> tuple[Vote, float]:
        """Wall-clock cap. A call that is still stuck from last tick abstains immediately."""
        prev = self._inflight.get(analyst.analyst_id)
        if prev is not None and not prev.done():
            self.stats["timeouts"] += 1
            log.warning("analyst %s still running from the last tick -> ABSTAIN", analyst.analyst_id)
            return Vote.abstain(analyst.analyst_id, "TIMEOUT"), 0.0
        if self._cap_pool is None:
            self._cap_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="analyst-cap")
        start = time.perf_counter()
        fut = self._cap_pool.submit(self._run, analyst, ctx)
        self._inflight[analyst.analyst_id] = fut
        try:
            vote = fut.result(timeout=limit)
        except FutureTimeout:
            self.stats["timeouts"] += 1
            log.warning("analyst %s timed out after %.0f ms -> ABSTAIN", analyst.analyst_id, limit * 1000.0)
            return Vote.abstain(analyst.analyst_id, "TIMEOUT"), (time.perf_counter() - start) * 1000.0
        except Exception as exc:
            self.stats["errors"] += 1
            log.warning("analyst %s crashed (%s: %s) -> ABSTAIN", analyst.analyst_id, type(exc).__name__, exc)
            return Vote.abstain(analyst.analyst_id, f"ERROR:{type(exc).__name__}"), (time.perf_counter() - start) * 1000.0
        return vote, (time.perf_counter() - start) * 1000.0

    def _collect_sync(self, ctx: MarketContext) -> list[tuple[Vote, float]]:
        """In order. Voting analysts have no wall-clock abstain. A capped analyst cannot stall the rest."""
        out: list[tuple[Vote, float]] = []
        for analyst in self.analysts:
            if self._replay_capped(analyst):
                out.append(self._run_capped(analyst, ctx, self.timeout_for(analyst)))
                continue
            start = time.perf_counter()
            try:
                vote = self._run(analyst, ctx)
            except Exception as exc:
                self.stats["errors"] += 1
                log.warning("analyst %s crashed (%s: %s) -> ABSTAIN", analyst.analyst_id, type(exc).__name__, exc)
                vote = Vote.abstain(analyst.analyst_id, f"ERROR:{type(exc).__name__}")
            out.append((vote, (time.perf_counter() - start) * 1000.0))
        self.stats["votes"] += len(out)
        return out

    def _collect_timed(self, ctx: MarketContext) -> list[tuple[Vote, float]]:
        """Parallel. Each analyst uses its own timeout (config ``timeout_ms`` or a per-key override)."""
        assert self._pool is not None
        start = time.perf_counter()
        futures = [self._pool.submit(self._run, a, ctx) for a in self.analysts]
        limits = [self.timeout_for(a) for a in self.analysts]
        pending = {fut: (analyst, limit) for fut, analyst, limit in zip(futures, self.analysts, limits)}
        done: dict[str, tuple[Vote, float]] = {}
        while pending:
            elapsed = time.perf_counter() - start
            for fut, (analyst, limit) in list(pending.items()):
                if fut.done():
                    done[analyst.analyst_id] = self._take(analyst, fut, elapsed * 1000.0)
                    del pending[fut]
                elif elapsed >= limit:
                    fut.cancel()
                    self.stats["timeouts"] += 1
                    log.warning("analyst %s timed out after %.0f ms -> ABSTAIN", analyst.analyst_id, elapsed * 1000.0)
                    done[analyst.analyst_id] = (Vote.abstain(analyst.analyst_id, "TIMEOUT"), elapsed * 1000.0)
                    del pending[fut]
            if not pending:
                break
            remaining = min(limit - (time.perf_counter() - start) for _a, limit in pending.values())
            wait(list(pending), timeout=max(0.0, remaining))
        out = [done[a.analyst_id] for a in self.analysts]
        self.stats["votes"] += len(out)
        return out

    def collect(self, ctx: MarketContext) -> list[tuple[Vote, float]]:
        """[(vote, latency_ms)] in registry order. Never raises."""
        if self.deterministic:
            return self._collect_sync(ctx)
        return self._collect_timed(ctx)

    def attach(self, bus: Any, contexts: dict[str, MarketContext], *, priority: int = 50) -> str:
        """Answer REQUEST_VOTES {request_id} with one ANALYST_VOTE per analyst.

        `contexts` maps request_id -> MarketContext (the boss fills it; contexts hold in-process
        engine state, only the request id and the votes travel as JSON).
        """

        def on_request(event: Any) -> None:
            p = event.payload
            ctx = contexts[p["request_id"]]
            for vote, ms in self.collect(ctx):
                payload = {
                    "request_id": p["request_id"], "underlying": ctx.underlying, "ts": ctx.ts,
                    "latency_ms": round(ms, 3), **vote.to_payload(),
                }
                if (vote.metadata or {}).get("shadow"):
                    payload["value"] = vote.metadata.get("value")
                    payload["flag"] = vote.metadata.get("flag")
                bus.publish("ANALYST_VOTE", payload, source=f"analyst:{vote.analyst_id}")

        return bus.subscribe(["REQUEST_VOTES"], on_request, priority=priority)

    def close(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
        if self._cap_pool is not None:
            self._cap_pool.shutdown(wait=False, cancel_futures=True)
