"""LLM advisor: provider call behind every guardrail. Advisory only; never raises; failure = abstain.

Guardrails, in order: cache (identical context -> same verdict, no call) -> signal reuse (same
underlying/side/strike reviewed < reuse_window_s of tick time ago -> that verdict) -> stale tick -> per-day
call budget -> per-day cost budget -> rate limit -> one call in flight -> hard wall-clock timeout
-> strict schema. Offline providers (mock / recorded) skip the budget and rate checks so replays
are deterministic. Every provider call is appended to a JSONL log (offline calls only if
`replay_log_path` is set).
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from desk_ml.llm_analyst.context import context_hash, scrub
from desk_ml.llm_analyst.providers import (
    PROMPT_VERSION, MockProvider, Provider, VerdictError, build_messages, make_provider, parse_verdict,
)

log = logging.getLogger("llm_analyst")
IST = timezone(timedelta(hours=5, minutes=30))
CONFIG_PATH = Path("config") / "llm_analyst.yaml"

DEFAULTS: dict[str, Any] = {
    "provider": "mock",
    "replay_provider": "mock",
    "model": "gpt-4o-mini",
    "weight": 0,
    "timeout_ms": 2000,
    "max_calls_per_day": 200,
    "max_cost_usd_per_day": 1.0,
    "min_interval_s": 2.0,
    "max_tick_age_s": 180,
    "cache_size": 5000,
    "reuse_window_s": 300,
    "max_output_tokens": 300,
    "price_usd_per_1m_tokens": {"input": 0.15, "output": 0.60},
    "log_path": "data/llm_analyst/calls.jsonl",
    "replay_log_path": None,
    "recorded_path": "data/llm_analyst/calls.jsonl",
    "premarket_brief_path": None,
}
ALLOWED_WEIGHTS = (0.0, 1.0)


def load_config(path: Optional[Path] = None, root: Optional[Path] = None) -> dict[str, Any]:
    """config/llm_analyst.yaml over DEFAULTS. Relative paths resolve against `root` (repo root)."""
    from desk_ml.persist import repo_root

    base = Path(root) if root is not None else repo_root()
    p = Path(path) if path is not None else base / CONFIG_PATH
    raw: dict[str, Any] = {}
    if p.is_file():
        import yaml

        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    unknown = sorted(set(raw) - set(DEFAULTS))
    if unknown:
        raise ValueError(f"unknown llm_analyst keys {unknown}")
    cfg = {**DEFAULTS, **raw}
    weight = float(cfg["weight"])
    if weight not in ALLOWED_WEIGHTS:
        # The picker is an unweighted CE/PE majority: 0 = shadow (log only), 1 = one vote.
        raise ValueError(f"llm_analyst weight must be 0 (shadow) or 1 (one picker vote), got {cfg['weight']!r}")
    cfg["weight"] = weight
    if not 50 <= int(cfg["timeout_ms"]) <= 10_000:
        raise ValueError("llm_analyst timeout_ms must be 50..10000")
    for key in ("log_path", "replay_log_path", "recorded_path", "premarket_brief_path"):
        if cfg[key]:
            q = Path(str(cfg[key]))
            cfg[key] = str(q if q.is_absolute() else base / q)
    return cfg


def abstain(status: str, h: str = "", **extra: Any) -> dict[str, Any]:
    return {"verdict": "abstain", "confidence": 0.0, "reasons": [], "risk_flags": [], "status": status,
            "context_hash": h, "cached": False, **extra}


class Advisor:
    """One per (config, mode) per process, so the cache and budgets survive the live loop's re-replays."""

    def __init__(self, cfg: Mapping[str, Any], *, replay: bool, clock: Callable[[], float] = time.time,
                 provider: Optional[Provider] = None) -> None:
        self.cfg = dict(cfg)
        self.replay = bool(replay)
        self.clock = clock
        name = self.cfg["replay_provider"] if self.replay else self.cfg["provider"]
        self.provider = provider or make_provider(name, self.cfg)
        if self.replay and not self.provider.offline:
            log.warning("replay_provider %s is online; replay uses the mock provider", name)
            self.provider = MockProvider(self.cfg)
        self.timeout_s = int(self.cfg["timeout_ms"]) / 1000.0
        # Online calls -> log_path (the record the scorer and `recorded` provider read). Offline
        # (mock / recorded) calls -> replay_log_path, off by default so replays write nothing.
        self.log_path = self.cfg["replay_log_path"] if self.provider.offline else self.cfg["log_path"]
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._day = ""
        self.calls_today = 0
        self.cost_today = 0.0
        self._last_call = float("-inf")
        self._bg: Optional[Future] = None
        self._last_by_signal: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
        # ponytail: a hung provider thread cannot be killed; the HTTP timeout equals the wall-clock cap,
        # so it frees itself soon after. Upgrade to a subprocess if a provider SDK ever ignores timeouts.
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="llm")
        self._bg_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm-bg")
        self.stats: dict[str, int] = {}
        if not self.provider.offline:
            self._seed_from_log()

    # ------------------------------------------------------------------ state

    def _bump(self, key: str) -> None:
        self.stats[key] = self.stats.get(key, 0) + 1

    def _ist_day(self) -> str:
        return datetime.fromtimestamp(self.clock(), IST).date().isoformat()

    def _roll_day(self) -> None:
        day = self._ist_day()
        if day != self._day:
            self._day, self.calls_today, self.cost_today = day, 0, 0.0

    def _cache_key(self, h: str) -> str:
        return f"{PROMPT_VERSION}|{self.provider.name}|{self.provider.model}|{h}"

    def _seed_from_log(self) -> None:
        """Today's spend and verdicts from the log, so a restart cannot reset the budget."""
        self._roll_day()
        path = Path(self.log_path) if self.log_path else None
        if path is None or not path.is_file():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict) or row.get("ist_date") != self._day or row.get("provider") != self.provider.name:
                continue
            self.calls_today += 1
            self.cost_today += float(row.get("cost_usd") or 0.0)
            if row.get("status") == "ok" and isinstance(row.get("verdict"), dict) and row.get("prompt_version") == PROMPT_VERSION \
                    and row.get("model") == self.provider.model:
                self._remember(self._cache_key(str(row.get("context_hash"))), {**row["verdict"], "status": "ok"})

    def _remember(self, key: str, outcome: dict[str, Any]) -> None:
        self._cache[key] = outcome
        self._cache.move_to_end(key)
        while len(self._cache) > int(self.cfg["cache_size"]):
            self._cache.popitem(last=False)

    # ------------------------------------------------------------------ review

    def review(self, context: Mapping[str, Any], *, background: bool = False) -> dict[str, Any]:
        """Verdict for this context. Never raises. `background=True` returns PENDING and logs later."""
        try:
            h = context_hash(context)
        except Exception as exc:  # unhashable context is a bug upstream; still abstain
            return abstain(f"BAD_CONTEXT:{type(exc).__name__}")
        try:
            with self._lock:
                hit = self._cache.get(self._cache_key(h))
                if hit is not None:
                    self._bump("cache_hits")
                    return {**hit, "context_hash": h, "cached": True}
                reused = self._reuse(context)
                if reused is not None:
                    self._bump("reused")
                    self._remember(self._cache_key(h), reused)
                    return {**reused, "context_hash": h, "cached": True}
                refused = self._refuse(context)
                if refused:
                    self._bump(refused)
                    return abstain(refused, h)
                if background:
                    self._bg = self._bg_pool.submit(self._call, context, h)
                    return abstain("PENDING", h)
            return self._call(context, h)
        except Exception as exc:
            log.exception("llm advisor failed -> abstain")
            return abstain(f"ERROR:{type(exc).__name__}", h)

    @staticmethod
    def _signal_key(context: Mapping[str, Any]) -> tuple[Any, ...]:
        sig = context.get("signal") or {}
        return (context.get("underlying"), sig.get("side"), sig.get("strike"))

    def _reuse(self, context: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        """Online only (it saves budget; offline replays stay one call per context)."""
        if self.provider.offline:
            return None
        last = self._last_by_signal.get(self._signal_key(context))
        tick_ts = context.get("tick_ts")
        if last is None or not isinstance(tick_ts, (int, float)):
            return None
        if 0 <= float(tick_ts) - last[0] < float(self.cfg["reuse_window_s"]):
            return {**last[1], "status": "reused"}
        return None

    def _refuse(self, context: Mapping[str, Any]) -> Optional[str]:
        """Called under the lock. Offline providers are free and deterministic: never refused."""
        if self.provider.offline:
            return None
        now = self.clock()
        self._roll_day()
        tick_ts = context.get("tick_ts")
        if isinstance(tick_ts, (int, float)) and now - float(tick_ts) > float(self.cfg["max_tick_age_s"]):
            return "STALE_TICK"
        if self.calls_today >= int(self.cfg["max_calls_per_day"]):
            return "BUDGET_CALLS"
        system, user = build_messages(context)
        if self.cost_today + self.provider.estimate_cost_usd(system, user) > float(self.cfg["max_cost_usd_per_day"]):
            return "BUDGET_COST"
        if now - self._last_call < float(self.cfg["min_interval_s"]):
            return "RATE_LIMITED"
        if self._bg is not None and not self._bg.done():
            return "BUSY"
        self._last_call = now
        self.calls_today += 1
        return None

    def _call(self, context: Mapping[str, Any], h: str) -> dict[str, Any]:
        system, user = build_messages(context)
        t0 = time.perf_counter()
        reply, verdict, status, error = None, None, "ok", None
        fut = self._pool.submit(
            self.provider.complete, system, user, context=context, context_hash=h, timeout_s=self.timeout_s,
        )
        try:
            reply = fut.result(timeout=self.timeout_s)
            verdict = parse_verdict(reply.text)
        except FutureTimeout:
            fut.cancel()
            status, error = "timeout", f"TIMEOUT_{int(self.timeout_s * 1000)}MS"
        except VerdictError as exc:
            status, error = "invalid", str(exc)[:200]
        except Exception as exc:
            status, error = "error", f"{type(exc).__name__}:{str(exc)[:120]}"
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        cost = float(reply.cost_usd) if reply is not None else 0.0
        outcome = {**(verdict or abstain(status)), "status": status}
        with self._lock:
            self.cost_today += cost
            self._bump(status)
            if status == "ok":
                self._remember(self._cache_key(h), outcome)
                if isinstance(context.get("tick_ts"), (int, float)):
                    self._last_by_signal[self._signal_key(context)] = (float(context["tick_ts"]), outcome)
            self._append({
                "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "ist_date": self._ist_day(),
                "mode": "replay" if self.replay else "live",
                "provider": self.provider.name,
                "model": self.provider.model,
                "prompt_version": PROMPT_VERSION,
                "context_hash": h,
                "underlying": context.get("underlying"),
                "tick_ts": context.get("tick_ts"),
                "side": (context.get("signal") or {}).get("side"),
                "strike": (context.get("signal") or {}).get("strike"),
                "status": status,
                "error": error,
                "verdict": verdict,
                "response": scrub(reply.text[:4000]) if reply is not None and isinstance(reply.text, str) else None,
                "latency_ms": latency_ms,
                "tokens_in": reply.tokens_in if reply is not None else 0,
                "tokens_out": reply.tokens_out if reply is not None else 0,
                "cost_usd": round(cost, 6),
                "context": dict(context),
            })
        return {**outcome, "context_hash": h, "cached": False, "latency_ms": latency_ms, "cost_usd": cost}

    def _append(self, row: dict[str, Any]) -> None:
        """Append-only JSONL. A write failure is logged, never raised into the trading loop."""
        if not self.log_path:
            return
        try:
            path = Path(self.log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str) + "\n")
        except OSError:
            log.exception("llm call log write failed (%s)", self.log_path)

    def wait_idle(self, timeout_s: float = 5.0) -> None:
        """Tests / shutdown: wait for a background review to finish."""
        bg = self._bg
        if bg is not None:
            try:
                bg.result(timeout=timeout_s)
            except Exception:
                pass

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
        self._bg_pool.shutdown(wait=False, cancel_futures=True)


_ADVISORS: dict[tuple[str, bool], Advisor] = {}
_ADVISORS_LOCK = threading.Lock()


def get_advisor(cfg: Mapping[str, Any], *, replay: bool) -> Advisor:
    """Process-wide advisor per (config, mode)."""
    key = (json.dumps(dict(cfg), sort_keys=True, default=str), bool(replay))
    with _ADVISORS_LOCK:
        if key not in _ADVISORS:
            _ADVISORS[key] = Advisor(cfg, replay=replay)
        return _ADVISORS[key]


def reset_advisors() -> None:
    with _ADVISORS_LOCK:
        for adv in _ADVISORS.values():
            adv.close()
        _ADVISORS.clear()
