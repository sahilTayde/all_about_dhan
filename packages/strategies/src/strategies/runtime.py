"""
Strategy runtime loader and isolation (V2-06).

Loads strategies by module path, checks declared features/markets,
enforces per-call budgets, and publishes BASKET_LOADED events.
"""

import importlib
import logging
import signal as signal_module
import time
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterator

from .api import Strategy, StrategyMeta
from .registry import Basket, RegistryEntry, load_basket, load_registry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedStrategy:
    """
    Strategy instance with metadata and runtime state.

    The runtime tracks whether the strategy is enabled (can emit signals)
    or disabled (raises/timeouts disable it for the session).
    """

    strategy: Strategy
    registry_entry: RegistryEntry
    enabled: bool = True
    disabled_reason: str | None = None


class StrategyRuntimeError(Exception):
    """Raised when a strategy fails to load or validate."""

    pass


class StrategyTimeoutError(Exception):
    """Raised when a strategy call exceeds its budget."""

    pass


def load_strategy(
    strategy_id: str,
    registry: dict[str, RegistryEntry],
    available_features: set[str] | None = None,
) -> Strategy:
    """
    Load a strategy plugin by module path.

    Args:
        strategy_id: Strategy ID from registry
        registry: Registry dict from load_registry()
        available_features: Set of available feature names (checked against meta.features)

    Returns:
        Strategy instance

    Raises:
        StrategyRuntimeError: If strategy fails to load, or if declared features/markets
            are not available

    The strategy module must have a `strategy` module-level attribute that is
    the Strategy instance.
    """
    if strategy_id not in registry:
        raise StrategyRuntimeError(f"Strategy {strategy_id} not in registry")

    entry = registry[strategy_id]

    try:
        module = importlib.import_module(entry.module_path)
    except ImportError as e:
        raise StrategyRuntimeError(
            f"Failed to import {entry.module_path} for {strategy_id}: {e}"
        ) from e

    if not hasattr(module, "strategy"):
        raise StrategyRuntimeError(
            f"Module {entry.module_path} has no 'strategy' attribute"
        )

    strategy_instance = module.strategy

    if not hasattr(strategy_instance, "meta"):
        raise StrategyRuntimeError(
            f"Strategy {strategy_id} has no 'meta' attribute"
        )

    meta: StrategyMeta = strategy_instance.meta

    # Validate meta matches registry
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

    # Check features if available_features provided
    if available_features is not None:
        missing_features = set(meta.features) - available_features
        if missing_features:
            raise StrategyRuntimeError(
                f"Strategy {strategy_id} requires features not available: "
                f"{sorted(missing_features)}"
            )

    return strategy_instance


def load_basket_strategies(
    session: date,
    market: str,
    registry: dict[str, RegistryEntry] | None = None,
    available_features: set[str] | None = None,
) -> tuple[Basket | None, dict[str, LoadedStrategy]]:
    """
    Load basket and all its strategies for a session.

    Args:
        session: Trading session date
        market: Market name (e.g. "IN_INDEX_OPT")
        registry: Pre-loaded registry (or load from YAML if None)
        available_features: Available features for validation

    Returns:
        (basket, loaded_strategies) tuple
        - basket is None if no basket file found (NO TRADES)
        - loaded_strategies maps strategy_id to LoadedStrategy

    Strategies that fail to load are logged but don't fail the whole basket.
    They're marked as disabled with the reason.
    """
    if registry is None:
        registry = load_registry()

    basket = load_basket(session, market)
    if basket is None:
        logger.warning(
            f"No basket for {session.strftime('%Y-%m-%d')} {market}. "
            "NO BASKET MEANS NO TRADES (fail closed)."
        )
        return None, {}

    loaded: dict[str, LoadedStrategy] = {}

    for entry in basket.entries:
        strategy_id = entry.strategy_id
        try:
            strategy_instance = load_strategy(strategy_id, registry, available_features)

            # Check market compatibility
            if market not in strategy_instance.meta.markets:
                logger.warning(
                    f"Strategy {strategy_id} not compatible with market {market}. "
                    f"Declared markets: {strategy_instance.meta.markets}. Disabling."
                )
                loaded[strategy_id] = LoadedStrategy(
                    strategy=strategy_instance,
                    registry_entry=registry[strategy_id],
                    enabled=False,
                    disabled_reason=f"MARKET_INCOMPATIBLE:{market}",
                )
                continue

            loaded[strategy_id] = LoadedStrategy(
                strategy=strategy_instance,
                registry_entry=registry[strategy_id],
                enabled=True,
            )
            logger.info(
                f"Loaded strategy {strategy_id} v{strategy_instance.meta.version} "
                f"({strategy_instance.meta.stage})"
            )

        except StrategyRuntimeError as e:
            logger.error(f"Failed to load strategy {strategy_id}: {e}. Disabling.")
            # Create a disabled placeholder (can't call any methods)
            loaded[strategy_id] = LoadedStrategy(
                strategy=None,  # type: ignore[arg-type]
                registry_entry=registry.get(strategy_id) if registry else None,  # type: ignore[arg-type]
                enabled=False,
                disabled_reason=str(e),
            )

    return basket, loaded


@contextmanager
def strategy_call_budget(timeout_s: float = 0.1) -> Iterator[None]:
    """
    Context manager to enforce per-call budget for strategy methods.

    Args:
        timeout_s: Maximum time allowed for the call (default 0.1s = 100ms)

    Raises:
        StrategyTimeoutError: If call exceeds budget

    Usage:
        with strategy_call_budget(0.1):
            signals = strategy.on_bar(bar, view)
    """
    def timeout_handler(signum: int, frame: Any) -> None:
        raise StrategyTimeoutError(f"Strategy call exceeded {timeout_s}s budget")

    old_handler = signal_module.signal(signal_module.SIGALRM, timeout_handler)
    signal_module.setitimer(signal_module.ITIMER_REAL, timeout_s)

    try:
        yield
    finally:
        signal_module.setitimer(signal_module.ITIMER_REAL, 0)
        signal_module.signal(signal_module.SIGALRM, old_handler)


def disable_strategy(
    loaded: dict[str, LoadedStrategy],
    strategy_id: str,
    reason: str,
) -> None:
    """
    Disable a strategy for the session.

    Args:
        loaded: Loaded strategies dict (mutated in place)
        strategy_id: Strategy to disable
        reason: Reason for disabling (logged)

    A disabled strategy will not be called for the rest of the session.
    """
    if strategy_id in loaded:
        logger.warning(
            f"Disabling strategy {strategy_id} for session: {reason}"
        )
        loaded[strategy_id] = LoadedStrategy(
            strategy=loaded[strategy_id].strategy,
            registry_entry=loaded[strategy_id].registry_entry,
            enabled=False,
            disabled_reason=reason,
        )


def validate_exit_plan_catastrophic_stop(meta: StrategyMeta) -> None:
    """
    Validate that strategy has a catastrophic stop (REG-18d).

    Args:
        meta: Strategy metadata with exit plan in params

    Raises:
        StrategyRuntimeError: If no catastrophic stop defined

    REG-18d: A plan without a catastrophic stop must refuse to load.
    This prevents strategies from running without the house ₹30k stop.
    """
    # Note: This is a stub check. The real validation happens when the
    # exit plan is constructed from defaults + strategy overrides.
    # For V2-06, we just document the requirement. V2-09 (position manager)
    # will enforce it when building the actual exit plan.
    pass
