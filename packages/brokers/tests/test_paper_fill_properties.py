"""P-O4 (spec §3/§6.6): PaperBroker(cost_model="realistic") fill prices.

- Every fill is on-tick (0.05).
- A buy never pays above its limit; a sell never receives below its limit.
- A LIMIT fills only on a trade-through (a print at least one tick beyond it), and only at the limit.
- Marketable fills (MARKET, triggered SL-M) never beat LTP +/- slippage.

Known-bad mutant: the legacy model (`cost_model="legacy"`, nearest-tick rounding and touch fills)
fails the first two bullets; `test_legacy_is_the_documented_mutant` pins that example.
"""

import math
import os
from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from brokers import OrderState, PaperBroker
from risk_engine import IST, RiskDecision, TradeIntent

settings.register_profile("ci", max_examples=300, derandomize=True, deadline=500)
settings.register_profile("nightly", max_examples=5000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

SYM = "NIFTY 25000 CE"
TICK = 0.05
premiums = st.integers(min_value=1, max_value=20_000).map(lambda n: n / 100)  # 0.01 .. 200.00, often off-tick


def on_tick(x):
    return abs(x / TICK - round(x / TICK)) < 1e-6


def place(broker, side, kind, *, price=None, trigger=None):
    intent = TradeIntent(symbol=SYM, side=side, lots=1, lot_size=65, order_type=kind, price=price,
                         trigger_price=trigger, purpose="ENTRY" if side == "BUY" else "EXIT",
                         exit_reason=None if side == "BUY" else "MANUAL")
    decision = RiskDecision(True, intent.client_order_id, broker.action_for(intent), "OK", "test", datetime.now(IST))
    return broker.place_order(intent, decision)


@given(st.sampled_from(["BUY", "SELL"]), premiums, st.lists(premiums, min_size=1, max_size=12))
def test_limit_fills_only_on_trade_through_and_only_at_the_limit(side, limit, ltps):
    broker = PaperBroker(slippage_ticks=2, cost_model="realistic")
    order = place(broker, side, "LIMIT", price=limit)
    n = round(limit / TICK, 6)
    resting = round((math.floor(n) if side == "BUY" else math.ceil(n)) * TICK, 2)
    crossed = False
    for ltp in ltps:
        broker.on_tick(SYM, ltp)
        crossed = crossed or (ltp <= resting - TICK + 1e-9 if side == "BUY" else ltp >= resting + TICK - 1e-9)
        crossed = crossed and resting >= TICK
    assert (order.state == OrderState.FILLED) == crossed
    if order.state == OrderState.FILLED:
        px = order.avg_fill_price
        assert on_tick(px) and px == resting
        assert px <= limit + 1e-9 if side == "BUY" else px >= limit - 1e-9


@given(st.sampled_from(["BUY", "SELL"]), st.sampled_from(["MARKET", "SL-M"]), premiums, premiums,
       st.integers(min_value=0, max_value=5))
def test_marketable_fills_are_on_tick_and_never_better_than_ltp_plus_slippage(side, kind, trigger, ltp, slip_ticks):
    broker = PaperBroker(slippage_ticks=slip_ticks, cost_model="realistic")
    order = place(broker, side, kind, trigger=trigger if kind == "SL-M" else None)
    broker.on_tick(SYM, ltp)
    if order.state != OrderState.FILLED:
        assert kind == "SL-M"  # trigger not touched
        return
    px, slip = order.avg_fill_price, slip_ticks * TICK
    assert on_tick(px) and px >= TICK
    assert px >= ltp + slip - 1e-9 if side == "BUY" else px <= max(TICK, ltp - slip) + 1e-9


def test_legacy_is_the_documented_mutant():
    legacy, realistic = PaperBroker(slippage_ticks=1), PaperBroker(slippage_ticks=1, cost_model="realistic")
    a, b = place(legacy, "BUY", "LIMIT", price=100.03), place(realistic, "BUY", "LIMIT", price=100.03)
    for broker in (legacy, realistic):
        broker.on_tick(SYM, 100.03)  # a touch, no trade-through
    assert a.state == OrderState.FILLED and a.avg_fill_price == 100.05 > 100.03  # legacy pays above its limit
    assert b.state == OrderState.SUBMITTED
    realistic.on_tick(SYM, 99.95)
    assert b.avg_fill_price == 100.0  # at the (tick-floored) limit, not the better print
