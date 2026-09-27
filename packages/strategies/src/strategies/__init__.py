"""V2 strategy runtime and registry. Paper only; never places orders."""

from contracts.payloads import StrikeChoice, StrikeQuote

from .api import (
    Bar,
    ChainSnapshot,
    EntryPolicy,
    ExitPlan,
    ExitRequest,
    PositionUpdate,
    SessionContext,
    Signal,
    Strategy,
    StrategyMeta,
)
from .feature_view_stub import FeatureView
from .params_hash import (
    ROUND11_DEFAULTS_SHA256,
    compute_params_hash,
    config_hash,
    exit_plan_hash,
    inherit_exit_defaults,
    load_exit_defaults,
    resolve_exit_plan,
)
from .registry import Basket, BasketEntry, RegistryEntry, basket_for, load_basket, load_registry
from .runtime import (
    HealthAlert,
    LoadedStrategy,
    SessionRuntime,
    StrategyRuntimeError,
    StrategyTimeoutError,
    basket_loaded_event,
    disable_strategy,
    load_basket_strategies,
    load_strategy,
    strategy_call_budget,
)
from .strikes import DatedQuote, StrikeRouter, load_router_rules, rule_version

__all__ = [
    "ROUND11_DEFAULTS_SHA256",
    "Bar",
    "Basket",
    "BasketEntry",
    "ChainSnapshot",
    "DatedQuote",
    "EntryPolicy",
    "ExitPlan",
    "ExitRequest",
    "FeatureView",
    "HealthAlert",
    "inherit_exit_defaults",
    "LoadedStrategy",
    "PositionUpdate",
    "RegistryEntry",
    "SessionContext",
    "SessionRuntime",
    "Signal",
    "Strategy",
    "StrategyMeta",
    "StrategyRuntimeError",
    "StrategyTimeoutError",
    "StrikeChoice",
    "StrikeQuote",
    "StrikeRouter",
    "basket_for",
    "basket_loaded_event",
    "compute_params_hash",
    "config_hash",
    "disable_strategy",
    "exit_plan_hash",
    "load_basket",
    "load_basket_strategies",
    "load_exit_defaults",
    "load_registry",
    "load_router_rules",
    "load_strategy",
    "resolve_exit_plan",
    "rule_version",
    "strategy_call_budget",
]
