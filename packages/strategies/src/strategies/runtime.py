"""Strategy runtime: load, isolate, budget, BASKET_LOADED (V2-06)."""

from __future__ import annotations

import importlib
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from contracts.payloads import ExitPlan

from .api import Bar, Signal, StrategyMeta
from .feature_view_stub import FeatureView
from .params_hash import ExitPlanLoadError, resolve_exit_plan
from .registry import Basket, RegistryEntry, load_basket, load_registry

logger = logging.getLogger(__name__)

DEFAULT_BUDGET_S = 0.02  # architecture §2.5: budget_ms default 20 ms


@dataclass(frozen=True)
class LoadedStrategy:
    """Loaded plugin plus session enablement."""

    strategy: object | None
    registry_entry: RegistryEntry | None
    enabled: bool = True
    disabled_reason: str | None = None


@dataclass
class HealthAlert:
    """Published when a plugin is disabled (raising / over-budget / refused)."""

    kind: str
    strategy_id: str
    reason: str


class StrategyRuntimeError(Exception):
    """Strategy failed to load or validate."""


class StrategyTimeoutError(Exception):
    """Strategy call exceeded its per-call budget."""


def load_strategy(
    strategy_id: str,
    registry: dict[str, RegistryEntry],
    available_features: set[str] | None = None,
    required_market: str | None = None,
) -> object:
    """Load a plugin by module path and refuse incompatible meta.

    Raises:
        StrategyRuntimeError: missing registry row, import failure, meta
            mismatch, missing features, market mismatch, or REG-18d.
    """
    if strategy_id not in registry:
        raise StrategyRuntimeError(f"Strategy {strategy_id} not in registry")
    entry = registry[strategy_id]
    try:
        module = importlib.import_module(entry.module_path)
    except ImportError as exc:
        raise StrategyRuntimeError(
            f"Failed to import {entry.module_path} for {strategy_id}: {exc}"
        ) from exc
    if not hasattr(module, "strategy"):
        raise StrategyRuntimeError(f"Module {entry.module_path} has no 'strategy' attribute")
    instance: Any = module.strategy
    if not hasattr(instance, "meta"):
        raise StrategyRuntimeError(f"Strategy {strategy_id} has no 'meta' attribute")
    meta: StrategyMeta = instance.meta
    if meta.strategy_id != strategy_id:
        raise StrategyRuntimeError(
            f"Strategy meta.strategy_id ({meta.strategy_id}) != registry id ({strategy_id})"
        )
    if meta.version != entry.version:
        raise StrategyRuntimeError(
            f"Strategy {strategy_id} version mismatch: "
            f"meta={meta.version}, registry={entry.version}"
        )
    if meta.params_hash != entry.params_hash:
        raise StrategyRuntimeError(
            f"Strategy {strategy_id} params_hash mismatch: "
            f"meta={meta.params_hash}, registry={entry.params_hash}"
        )
    if available_features is not None:
        missing = set(meta.features) - available_features
        if missing:
            raise StrategyRuntimeError(
                f"Strategy {strategy_id} requires features not available: {sorted(missing)}"
            )
    if required_market is not None and required_market not in meta.markets:
        raise StrategyRuntimeError(
            f"Strategy {strategy_id} refuses to load into {required_market} "
            f"(declared markets: {meta.markets})"
        )
    _require_catastrophic(instance)
    return instance


def _require_catastrophic(instance: Any) -> ExitPlan:
    """REG-18d: refuse a plan with no catastrophic stop."""
    plan = getattr(instance, "exit_plan", None)
    if isinstance(plan, ExitPlan):
        if plan.catastrophic is None:
            raise StrategyRuntimeError(
                "REG-18d: a plan without a catastrophic stop refuses to load"
            )
        return plan
    if isinstance(plan, dict):
        try:
            return resolve_exit_plan(plan)
        except ExitPlanLoadError as exc:
            raise StrategyRuntimeError(str(exc)) from exc
    raise StrategyRuntimeError("REG-18d: a plan without a catastrophic stop refuses to load")


def load_basket_strategies(
    session: date,
    market: str,
    registry: dict[str, RegistryEntry] | None = None,
    available_features: set[str] | None = None,
) -> tuple[Basket | None, dict[str, LoadedStrategy], list[HealthAlert]]:
    """Load the session basket. Missing basket → zero strategies, one alert."""
    if registry is None:
        registry = load_registry()
    basket = load_basket(session, market)
    alerts: list[HealthAlert] = []
    if basket is None:
        logger.warning(
            "No basket for %s %s. NO BASKET MEANS NO TRADES (fail closed).",
            session.strftime("%Y-%m-%d"),
            market,
        )
        alerts.append(HealthAlert(kind="MISSING_BASKET", strategy_id="*", reason="no basket file"))
        return None, {}, alerts

    loaded: dict[str, LoadedStrategy] = {}
    for entry in basket.entries:
        sid = entry.strategy_id
        try:
            instance = load_strategy(sid, registry, available_features, required_market=market)
            loaded[sid] = LoadedStrategy(
                strategy=instance, registry_entry=registry.get(sid), enabled=True
            )
        except StrategyRuntimeError as exc:
            logger.error("Failed to load strategy %s: %s. Disabling.", sid, exc)
            loaded[sid] = LoadedStrategy(
                strategy=None,
                registry_entry=registry.get(sid),
                enabled=False,
                disabled_reason=str(exc),
            )
            alerts.append(HealthAlert(kind="STRATEGY_REFUSED", strategy_id=sid, reason=str(exc)))
    return basket, loaded, alerts


def basket_loaded_event(basket: Basket) -> dict[str, Any]:
    """`BASKET_LOADED {basket_hash, entries}` published at session start."""
    return {
        "event_type": "BASKET_LOADED",
        "basket_hash": basket.basket_hash,
        "entries": [
            {
                "strategy_id": e.strategy_id,
                "underlyings": list(e.underlyings),
                "weight": e.weight,
                "max_lots": e.max_lots,
                "stage": e.stage,
            }
            for e in basket.entries
        ],
    }


@contextmanager
def strategy_call_budget(timeout_s: float = DEFAULT_BUDGET_S) -> Iterator[None]:
    """Enforce a wall-clock budget on one strategy call (thread-safe).

    Measures elapsed time so the guard works off the main thread. SIGALRM
    is not used: installing it off the main thread raised and disabled
    every healthy plugin.
    """
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - start
    if elapsed > timeout_s:
        raise StrategyTimeoutError(f"Strategy call exceeded {timeout_s}s budget")


def _stage_of(row: LoadedStrategy, strategy_id: str) -> str:
    if row.registry_entry is not None and row.registry_entry.stage:
        return row.registry_entry.stage
    meta = getattr(row.strategy, "meta", None)
    stage = getattr(meta, "stage", None)
    if isinstance(stage, str) and stage:
        return stage
    del strategy_id
    return "shadow"


def emission_approved(strategy_id: str, stage: str) -> bool:
    """Shadow may emit. Any other stage needs a preregistered forward spec."""
    if stage == "shadow":
        return True
    spec = Path("config/v2/forward/specs") / f"{strategy_id}.yaml"
    return spec.is_file()


def disable_strategy(loaded: dict[str, LoadedStrategy], strategy_id: str, reason: str) -> None:
    """Disable one strategy for the rest of the session."""
    if strategy_id not in loaded:
        return
    logger.warning("Disabling strategy %s for session: %s", strategy_id, reason)
    current = loaded[strategy_id]
    loaded[strategy_id] = LoadedStrategy(
        strategy=current.strategy,
        registry_entry=current.registry_entry,
        enabled=False,
        disabled_reason=reason,
    )


@dataclass
class SessionRuntime:
    """Call enabled plugins in isolation. A raise disables only that plugin."""

    loaded: dict[str, LoadedStrategy]
    budget_s: float = DEFAULT_BUDGET_S
    alerts: list[HealthAlert] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]:
        emitted: list[Signal] = []
        for sid, row in list(self.loaded.items()):
            if not row.enabled or row.strategy is None:
                continue
            on_bar = getattr(row.strategy, "on_bar", None)
            if on_bar is None:
                continue
            stage = _stage_of(row, sid)
            if not emission_approved(sid, stage):
                logger.warning(
                    "refusing to emit for %s: stage %s is not onboarding-approved",
                    sid,
                    stage,
                )
                continue
            try:
                with strategy_call_budget(self.budget_s):
                    out = on_bar(bar, view)
                    if out is None:
                        out = []
                    if not isinstance(out, list):
                        raise TypeError(f"on_bar must return a list, got {type(out).__name__}")
            except BaseException as exc:
                reason = f"RAISED:{type(exc).__name__}:{exc}"
                logger.warning("strategy %s isolated: %s", sid, reason)
                disable_strategy(self.loaded, sid, reason)
                self.alerts.append(
                    HealthAlert(kind="STRATEGY_DISABLED", strategy_id=sid, reason=reason)
                )
                continue
            if out:
                emitted.extend(out)
                self.signals.extend(out)
        return emitted
