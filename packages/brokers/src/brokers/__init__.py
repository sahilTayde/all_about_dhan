"""Broker adapters (paper default, Dhan behind the live gate) + order state machine + reconciliation.

`brokers.dhan` is not imported here so paper-only users do not need dhan_client/httpx.
"""

from brokers.orders import (
    TERMINAL,
    TRANSITIONS,
    BrokerAdapter,
    InvalidTransition,
    LiveOrderRefused,
    Order,
    OrderRefused,
    OrderSnapshot,
    OrderState,
    Position,
    attach_ledger,
    exit_intent,
)
from brokers.paper import PaperBroker
from brokers.reconcile import Mismatch, compare_orders, compare_positions, reconcile

__all__ = [
    "TERMINAL",
    "TRANSITIONS",
    "BrokerAdapter",
    "InvalidTransition",
    "LiveOrderRefused",
    "Mismatch",
    "Order",
    "OrderRefused",
    "OrderSnapshot",
    "OrderState",
    "PaperBroker",
    "Position",
    "attach_ledger",
    "compare_orders",
    "compare_positions",
    "exit_intent",
    "reconcile",
]
