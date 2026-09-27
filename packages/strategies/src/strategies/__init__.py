"""V2 strategy runtime and registry. Paper only; never places orders."""

from contracts.payloads import StrikeChoice, StrikeQuote

from .api import (
    Bar,
    ChainSnapshot,
    ExitPlan,
    ExitRequest,
    PositionUpdate,
    SessionContext,
    Signal,
    Strategy,
    StrategyMeta,
)
from .feature_view_stub import FeatureView
from .params_hash import compute_params_hash, exit_plan_hash
from .registry import Basket, BasketEntry, RegistryEntry, load_basket, load_registry
from .runtime import (
    LoadedStrategy,
    StrategyRuntimeError,
    StrategyTimeoutError,
    disable_strategy,
    load_basket_strategies,
    load_strategy,
    strategy_call_budget,
)
from .strikes import DatedQuote, StrikeRouter, load_router_rules, rule_version

__all__ = [
    "Bar",
    "Basket",
    "BasketEntry",
    "ChainSnapshot",
    "DatedQuote",
    "ExitPlan",
    "ExitRequest",
    "FeatureView",
    "LoadedStrategy",
    "PositionUpdate",
    "RegistryEntry",
    "SessionContext",
    "Signal",
    "Strategy",
    "StrategyMeta",
    "StrategyRuntimeError",
    "StrategyTimeoutError",
    "StrikeChoice",
    "StrikeQuote",
    "StrikeRouter",
    "compute_params_hash",
    "disable_strategy",
    "exit_plan_hash",
    "load_basket",
    "load_basket_strategies",
    "load_registry",
    "load_router_rules",
    "load_strategy",
    "rule_version",
    "strategy_call_budget",
]
