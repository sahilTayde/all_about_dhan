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

    wanted = list(keys) if keys is not None else default_keys()
    unknown = [k for k in wanted if k not in REGISTRY]
    if unknown:
        raise ValueError(f"unknown analyst keys {unknown}; registered: {sorted(REGISTRY)}")
    return [REGISTRY[k]() for k in wanted]


def load_config(path: Optional[Path] = None) -> dict[str, Any]:
    """config/analysts.yaml -> {"analysts": [keys], "timeout_ms": int}. Missing file = defaults."""
    cfg: dict[str, Any] = {}
    if path is not None and Path(path).is_file():
        cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    keys = cfg.get("analysts") or default_keys()
    return {"analysts": [str(k) for k in keys], "timeout_ms": int(cfg.get("timeout_ms") or DEFAULT_TIMEOUT_S * 1000)}


class AnalystRoom:
    """Runs every analyst on a context in parallel; each gets `timeout_s` from the request.

    ponytail: Python threads cannot be killed, so a hung analyst keeps its worker; the room has
    one worker per analyst, so one hang costs that analyst's slot only. Upgrade to a process pool
    if an analyst ever wraps blocking I/O.
    """

    def __init__(self, analysts: Sequence[Analyst], *, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        ids = [a.analyst_id for a in analysts]
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate analyst ids {ids}")
        self.analysts = list(analysts)
        self.timeout_s = float(timeout_s)
        self._pool = ThreadPoolExecutor(max_workers=max(1, len(self.analysts)), thread_name_prefix="analyst")
        self.stats = {"votes": 0, "timeouts": 0, "errors": 0}

    @classmethod
    def from_config(cls, path: Optional[Path] = None) -> "AnalystRoom":
        cfg = load_config(path)
        return cls(build(cfg["analysts"]), timeout_s=cfg["timeout_ms"] / 1000.0)

    @property
    def analyst_ids(self) -> list[str]:
        return [a.analyst_id for a in self.analysts]

    def _run(self, analyst: Analyst, ctx: MarketContext) -> Vote:
        vote = analyst.vote(ctx)
        if not isinstance(vote, Vote) or vote.analyst_id != analyst.analyst_id:
            raise TypeError(f"{analyst.analyst_id} returned {vote!r}, not its own Vote")
        return vote

    def collect(self, ctx: MarketContext) -> list[tuple[Vote, float]]:
        """[(vote, latency_ms)] in registry order. Never raises."""
        start = time.perf_counter()
        futures = [self._pool.submit(self._run, a, ctx) for a in self.analysts]
        wait(futures, timeout=self.timeout_s)
        out: list[tuple[Vote, float]] = []
        for analyst, fut in zip(self.analysts, futures):
            ms = (time.perf_counter() - start) * 1000.0
            if not fut.done():
                fut.cancel()
                self.stats["timeouts"] += 1
                log.warning("analyst %s timed out after %.0f ms -> ABSTAIN", analyst.analyst_id, ms)
                out.append((Vote.abstain(analyst.analyst_id, "TIMEOUT"), ms))
                continue
            exc = fut.exception()
            if exc is not None:
                self.stats["errors"] += 1
                log.warning("analyst %s crashed (%s: %s) -> ABSTAIN", analyst.analyst_id, type(exc).__name__, exc)
                out.append((Vote.abstain(analyst.analyst_id, f"ERROR:{type(exc).__name__}"), ms))
                continue
            out.append((fut.result(), ms))
        self.stats["votes"] += len(out)
        return out

    def attach(self, bus: Any, contexts: dict[str, MarketContext], *, priority: int = 50) -> str:
        """Answer REQUEST_VOTES {request_id} with one ANALYST_VOTE per analyst.

        `contexts` maps request_id -> MarketContext (the boss fills it; contexts hold in-process
        engine state, only the request id and the votes travel as JSON).
        """

        def on_request(event: Any) -> None:
            p = event.payload
            ctx = contexts[p["request_id"]]
            for vote, ms in self.collect(ctx):
                bus.publish(
                    "ANALYST_VOTE",
                    {"request_id": p["request_id"], "underlying": ctx.underlying, "ts": ctx.ts,
                     "latency_ms": round(ms, 3), **vote.to_payload()},
                    source=f"analyst:{vote.analyst_id}",
                )

        return bus.subscribe(["REQUEST_VOTES"], on_request, priority=priority)

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
