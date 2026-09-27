"""V2-08b runtime demo: chase send, timeout miss, stretch record. Paper only."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from brokers.fills import Quote
from contracts.clock import IST, SimClock
from contracts.payloads import Decision
from risk_engine import V2RiskEngine

from oms import Account, MemoryLedger, OrderRouter
from oms.planner import OrderPlanner, load_entry_config

NOW = datetime(2026, 9, 28, 10, 1, tzinfo=IST)
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
SIG = "sg_demo_nifty_20260928_1001_0"


def _decision() -> Decision:
    return Decision(
        decision_id="dc_demo",
        underlying="NIFTY",
        decision="ENTER",
        signal_ids=[SIG],
        instrument_id=INST,
        lots=2,
        lot_size=65,
        stretch={
            "record_only": True,
            "zone_atr": 1.6,
            "zone": "fvg",
            "ema20_atr": 2.4,
            "twap_atr": 3.1,
        },
        entry_location={
            "signal_candle_atr": 2.4,
            "entry_distance_atr": 1.6,
            "nearest": {"zone": "fvg", "price": 24501.5, "distance_atr": 1.6},
        },
    )


def main() -> None:
    clock = SimClock(NOW)
    store = MemoryLedger()
    risk = V2RiskEngine(ledger=store, config_path=Path("config/risk_limits.yaml"))
    router = OrderRouter(clock=clock, risk=risk, store=store)
    planner = OrderPlanner(clock=clock, router=router, config=load_entry_config(), store=store)
    print(f"now={clock.now().isoformat()} stretch={_decision().stretch}")
    planner.on_decision(
        _decision(),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=NOW - timedelta(seconds=1),
    )
    planner.on_quote(Quote(clock.now(), 151.00, 151.20, 151.10, INST))
    order = next(iter(router.broker.orders.values()))
    print(f"sent {order.intent.order_type} @{order.intent.price} (never MARKET)")
    clock.advance_by(timedelta(seconds=2))
    planner.on_clock()
    row = next(iter(store.entry_plans.values()))
    print(f"timeout status={row['status']} reason={order.cancel_reason}")
    clock.advance_by(timedelta(seconds=0.4))
    planner.on_quote(Quote(clock.now(), 151.00, 151.18, 151.10, INST))
    clock.advance_by(timedelta(seconds=5))
    planner.on_clock()
    print(f"missed_chase shadow={row['result'].shadow}")


if __name__ == "__main__":
    main()
