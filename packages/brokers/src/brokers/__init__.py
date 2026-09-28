"""Broker adapters (paper default, Dhan behind the live gate) + order state machine.

`brokers.dhan` is not imported here so paper-only users do not need dhan_client/httpx.
"""

from brokers.factory import LiveBrokerDisabled, live_brokers_enabled, make_broker
from brokers.fills import ClockedPaperBroker, DepthFill, FcMeasFill, Quote, choose_fill
from brokers.orders import (
    TERMINAL,
    TRANSITIONS,
    BrokerAdapter,
    InvalidTransition,
    LedgerWriteFailed,
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
    "ClockedPaperBroker",
    "DepthFill",
    "FcMeasFill",
    "InvalidTransition",
    "LedgerWriteFailed",
    "LiveBrokerDisabled",
    "LiveOrderRefused",
    "Mismatch",
    "Order",
    "OrderRefused",
    "OrderSnapshot",
    "OrderState",
    "PaperBroker",
    "Position",
    "Quote",
    "attach_ledger",
    "choose_fill",
    "compare_orders",
    "compare_positions",
    "exit_intent",
    "live_brokers_enabled",
    "make_broker",
    "reconcile",
]
