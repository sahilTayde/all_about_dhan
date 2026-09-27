"""LLM advisor: provider call behind every guardrail. Advisory only; never raises; failure = abstain.

Guardrails, in order: cache (identical context -> same verdict, no call) -> signal reuse (same
underlying/side/strike reviewed < reuse_window_s of tick time ago -> that verdict) -> stale tick -> per-day
call budget -> per-day token-cost budget -> rate limit -> one call in flight -> hard wall-clock timeout
-> strict schema. Online and offline advisors for the same config share one call and token ledger.
Offline providers (mock / recorded) still always answer, so a replay stays deterministic; their calls
are counted on that same ledger, and the rate limit, stale-tick skip and cost refusal stay online-only.
Every provider call is appended to a JSONL log (offline calls only if `replay_log_path` is set).
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


class DayBudget:
    """One day's call count and token spend. Shared by the online and offline advisors of one config."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.day = ""
        self.calls = 0
        self.tokens = 0
        self.cost = 0.0
        self.seeded = False


_BUDGETS: dict[str, DayBudget] = {}
_BUDGETS_LOCK = threading.Lock()


def _budget_key(cfg: Mapping[str, Any]) -> str:
    """Same config shares a ledger. The replay flag is not part of the key."""
    return json.dumps(
        {
            "max_calls_per_day": cfg.get("max_calls_per_day"),
            "max_cost_usd_per_day": cfg.get("max_cost_usd_per_day"),
            "model": cfg.get("model"),
            "log_path": cfg.get("log_path"),
            "replay_log_path": cfg.get("replay_log_path"),
        },
        sort_keys=True,
        default=str,
    )


def shared_budget(cfg: Mapping[str, Any]) -> DayBudget:
    key = _budget_key(cfg)
    with _BUDGETS_LOCK:
        budget = _BUDGETS.get(key)
        if budget is None:
            budget = DayBudget()
            _BUDGETS[key] = budget
        return budget


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
        self.budget = shared_budget(self.cfg)
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._last_call = float("-inf")
        self._bg: Optional[Future] = None
        self._last_by_signal: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
        # ponytail: a hung provider thread cannot be killed; the HTTP timeout equals the wall-clock cap,
        # so it frees itself soon after. Upgrade to a subprocess if a provider SDK ever ignores timeouts.
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="llm")
        self._bg_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm-bg")
        self.stats: dict[str, int] = {}
        self._seed_from_log()

    # ------------------------------------------------------------------ state

    @property
    def calls_today(self) -> int:
        return self.budget.calls

    @property
    def cost_today(self) -> float:
        return self.budget.cost

    def _bump(self, key: str) -> None:
        self.stats[key] = self.stats.get(key, 0) + 1

    def _ist_day(self) -> str:
        return datetime.fromtimestamp(self.clock(), IST).date().isoformat()

    def _roll_day(self) -> None:
        """Move the shared ledger onto this clock's IST day. Never rewind: a replay clock must not wipe today's spend."""
        day = self._ist_day()
        with self.budget.lock:
            if self.budget.day and day <= self.budget.day:
                return
            self.budget.day = day
            self.budget.calls = 0
            self.budget.tokens = 0
            self.budget.cost = 0.0
            self.budget.seeded = False

    def _cache_key(self, h: str) -> str:
        return f"{PROMPT_VERSION}|{self.provider.name}|{self.provider.model}|{h}"

    def _log_rows(self) -> list[dict[str, Any]]:
        """Online and offline logs. The shared ledger counts both; a path listed twice is read once."""
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in (self.cfg.get("log_path"), self.cfg.get("replay_log_path")):
            if not raw or str(raw) in seen:
                continue
            seen.add(str(raw))
            path = Path(str(raw))
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
        return rows

    def _seed_from_log(self) -> None:
        """Today's spend from the logs, once per ledger, so a restart cannot reset or double-count it."""
        day = self._ist_day()
        calls, cost, tokens = 0, 0.0, 0
        cache_rows: list[tuple[str, dict[str, Any]]] = []
        for row in self._log_rows():
            if row.get("ist_date") != day:
                continue
            calls += 1
            cost += float(row.get("cost_usd") or 0.0)
            tokens += int(row.get("tokens_in") or 0) + int(row.get("tokens_out") or 0)
            if row.get("provider") == self.provider.name and row.get("status") == "ok" \
                    and isinstance(row.get("verdict"), dict) and row.get("prompt_version") == PROMPT_VERSION \
                    and row.get("model") == self.provider.model:
                cache_rows.append((self._cache_key(str(row.get("context_hash"))), {**row["verdict"], "status": "ok"}))
        with self.budget.lock:
            # Same rule as _roll_day: a later IST day replaces the ledger; an earlier clock does not.
            if not self.budget.day or day > self.budget.day:
                self.budget.day = day
                self.budget.calls = 0
                self.budget.tokens = 0
                self.budget.cost = 0.0
                self.budget.seeded = False
            if self.budget.day == day and not self.budget.seeded:
                self.budget.calls = calls
                self.budget.cost = cost
                self.budget.tokens = tokens
                self.budget.seeded = True
        for key, outcome in cache_rows:
            self._remember(key, outcome)

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
        """Called under the lock. Offline calls count, and are never refused (replay stays deterministic)."""
        now = self.clock()
        self._roll_day()
        if self.provider.offline:
            with self.budget.lock:
                self.budget.calls += 1
            return None
        tick_ts = context.get("tick_ts")
        if isinstance(tick_ts, (int, float)) and now - float(tick_ts) > float(self.cfg["max_tick_age_s"]):
            return "STALE_TICK"
        system, user = build_messages(context)
        estimate = self.provider.estimate_cost_usd(system, user)
        with self.budget.lock:
            if self.budget.calls >= int(self.cfg["max_calls_per_day"]):
                return "BUDGET_CALLS"
            if self.budget.cost + estimate > float(self.cfg["max_cost_usd_per_day"]):
                return "BUDGET_COST"
            if now - self._last_call < float(self.cfg["min_interval_s"]):
                return "RATE_LIMITED"
            if self._bg is not None and not self._bg.done():
                return "BUSY"
            self._last_call = now
            self.budget.calls += 1
        return None

    def _invoke(self, system: str, user: str, context: Mapping[str, Any], h: str) -> tuple[Any, Any, str, Optional[str]]:
        reply = None
        try:
            reply = self.provider.complete(system, user, context=context, context_hash=h, timeout_s=self.timeout_s)
            return reply, parse_verdict(reply.text), "ok", None
        except VerdictError as exc:
            return reply, None, "invalid", str(exc)[:200]
        except Exception as exc:
            return reply, None, "error", f"{type(exc).__name__}:{str(exc)[:120]}"

    def _call(self, context: Mapping[str, Any], h: str) -> dict[str, Any]:
        system, user = build_messages(context)
        t0 = time.perf_counter()
        # Offline providers are in-process. A thread per replay tick is pure overhead; the room's
        # replay cap is what stops a hang. Online calls keep the hard wall-clock timeout.
        if self.provider.offline:
            reply, verdict, status, error = self._invoke(system, user, context, h)
        else:
            reply, verdict, status, error = None, None, "ok", None
            fut = self._pool.submit(self._invoke, system, user, context, h)
            try:
                reply, verdict, status, error = fut.result(timeout=self.timeout_s)
            except FutureTimeout:
                fut.cancel()
                status, error = "timeout", f"TIMEOUT_{int(self.timeout_s * 1000)}MS"
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        cost = float(reply.cost_usd) if reply is not None else 0.0
        tokens = (int(reply.tokens_in) + int(reply.tokens_out)) if reply is not None else 0
        outcome = {**(verdict or abstain(status)), "status": status}
        with self._lock:
            with self.budget.lock:
                self.budget.cost += cost
                self.budget.tokens += tokens
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
    with _BUDGETS_LOCK:
        _BUDGETS.clear()
