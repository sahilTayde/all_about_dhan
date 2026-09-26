"""Every order state transition: allowed ones succeed and are logged, all others raise."""

import logging

import pytest

from brokers import TERMINAL, TRANSITIONS, InvalidTransition, Order, OrderState
from risk_engine import TradeIntent

S = OrderState
VALID = [(a, b) for a, targets in TRANSITIONS.items() for b in targets]
INVALID = [(a, b) for a in S for b in S if (a, b) not in VALID]


def make(state=S.NEW, lots=1):
    seen = []
    order = Order(intent=TradeIntent(symbol="NIFTY 25000 CE", side="BUY", lots=lots, lot_size=65),
                  broker="paper", state=state, on_transition=lambda o, a, b, r: seen.append((a, b, r)))
    return order, seen


def test_transition_table_is_the_spec():
    assert VALID and sorted((a.value, b.value) for a, b in VALID) == sorted([
        ("NEW", "SUBMITTED"), ("NEW", "REJECTED"), ("NEW", "CANCELLED"),
        ("SUBMITTED", "PARTIAL"), ("SUBMITTED", "FILLED"), ("SUBMITTED", "REJECTED"),
        ("SUBMITTED", "CANCELLED"), ("SUBMITTED", "EXPIRED"),
        ("PARTIAL", "PARTIAL"), ("PARTIAL", "FILLED"), ("PARTIAL", "CANCELLED"), ("PARTIAL", "EXPIRED"),
    ])
    assert TERMINAL == {S.FILLED, S.REJECTED, S.CANCELLED, S.EXPIRED}
    assert not any(s in TRANSITIONS for s in TERMINAL)


@pytest.mark.parametrize("src,dst", VALID, ids=lambda s: s.value)
def test_valid_transition_is_applied_and_logged(src, dst, caplog):
    order, seen = make(src)
    with caplog.at_level(logging.INFO, logger="brokers"):
        order.transition(dst, "because")
    assert order.state == dst
    assert order.history[-1]["from"] == src.value and order.history[-1]["to"] == dst.value
    assert order.history[-1]["reason"] == "because" and order.history[-1]["ts"]
    assert seen == [(src, dst, "because")]
    assert f"{src.value} -> {dst.value}" in caplog.text


@pytest.mark.parametrize("src,dst", INVALID, ids=lambda s: s.value)
def test_invalid_transition_raises_and_changes_nothing(src, dst):
    order, seen = make(src)
    with pytest.raises(InvalidTransition):
        order.transition(dst)
    assert order.state == src and order.history == [] and seen == []


def test_fills_drive_partial_then_filled():
    order, seen = make(S.SUBMITTED, lots=2)  # 130 qty
    order.apply_fill(65, 100.0)
    assert order.state == S.PARTIAL and order.remaining_qty == 65
    order.apply_fill(65, 102.0)
    assert order.state == S.FILLED and order.avg_fill_price == 101.0
    assert [(a.value, b.value) for a, b, _ in seen] == [("SUBMITTED", "PARTIAL"), ("PARTIAL", "FILLED")]


def test_bad_fills_raise():
    order, _ = make(S.NEW)
    with pytest.raises(InvalidTransition):
        order.apply_fill(65, 100.0)
    order, _ = make(S.SUBMITTED)
    with pytest.raises(ValueError):
        order.apply_fill(66, 100.0)
    with pytest.raises(ValueError):
        order.apply_fill(0, 100.0)
