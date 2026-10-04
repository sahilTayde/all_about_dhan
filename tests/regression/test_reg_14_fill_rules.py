"""REG-14a-e: limits fill only on trade-through at the limit; stops never better than trigger."""

from __future__ import annotations

import random

from brokers.fills import limit_fill_price, stop_fill_price


def test_reg_14a_touch_is_not_a_fill() -> None:
    assert limit_fill_price(100.00, 100.00, "BUY") is None
    assert limit_fill_price(100.00, 100.00, "SELL") is None


def test_reg_14b_one_tick_through_fills_at_limit() -> None:
    assert limit_fill_price(99.95, 100.00, "BUY") == 100.00
    assert limit_fill_price(100.05, 100.00, "SELL") == 100.00


def test_reg_14c_overshoot_still_fills_at_limit_never_the_print() -> None:
    assert limit_fill_price(90.00, 100.00, "BUY") == 100.00
    assert limit_fill_price(120.00, 100.00, "SELL") == 100.00


def test_reg_14d_stop_fills_at_or_worse_than_trigger() -> None:
    # sell stop triggered by a gap print 90, slip 0.20 → 89.80 ≤ 100
    sell = stop_fill_price(90.00, 100.00, "SELL", 0.20)
    assert sell is not None and sell <= 100.00
    assert sell == 89.80
    # buy stop triggered by a gap print 110, slip 0.20 → 110.20 ≥ 100
    buy = stop_fill_price(110.00, 100.00, "BUY", 0.20)
    assert buy is not None and buy >= 100.00
    assert buy == 110.20


def test_reg_14e_property_limits_never_better_stops_never_better() -> None:
    rng = random.Random(14)
    for _ in range(400):
        side = rng.choice(["BUY", "SELL"])
        limit = rng.randint(20, 4000) / 20  # on or off a 0.05 grid
        print_px = rng.randint(1, 8000) / 20
        got = limit_fill_price(print_px, limit, side)
        if got is not None:
            if side == "BUY":
                assert got <= limit + 1e-9
            else:
                assert got >= limit - 1e-9
        trigger = rng.randint(20, 4000) / 20
        slip = rng.choice([0.05, 0.10, 0.20, 0.35])
        stop = stop_fill_price(print_px, trigger, side, slip)
        if stop is not None:
            if side == "BUY":
                assert stop + 1e-9 >= trigger
            else:
                assert stop <= trigger + 1e-9
