"""V2-25 Dhan off-market shadow order harness. Default OFF. No live trading."""

from harness.broker import MockOrderBroker, OrderPathBroker, make_broker
from harness.gates import (
    APPROVAL_ENV,
    APPROVAL_VALUE,
    EXIT_OK,
    EXIT_ORDER_PATH,
    EXIT_REFUSED,
    GateDecision,
    HarnessRefused,
    evaluate_gates,
)
from harness.order import (
    DEFAULT_OFF_MARKET_LIMIT,
    MAX_OFF_MARKET_LIMIT,
    HarnessOrderError,
    OffMarketIntent,
    default_intent,
    validate_off_market,
)
from harness.run import HarnessResult, run_shadow_test

__version__ = "0.1.0+aad"

__all__ = [
    "APPROVAL_ENV",
    "APPROVAL_VALUE",
    "DEFAULT_OFF_MARKET_LIMIT",
    "EXIT_OK",
    "EXIT_ORDER_PATH",
    "EXIT_REFUSED",
    "MAX_OFF_MARKET_LIMIT",
    "GateDecision",
    "HarnessOrderError",
    "HarnessRefused",
    "HarnessResult",
    "MockOrderBroker",
    "OffMarketIntent",
    "OrderPathBroker",
    "__version__",
    "default_intent",
    "evaluate_gates",
    "make_broker",
    "run_shadow_test",
    "validate_off_market",
]
