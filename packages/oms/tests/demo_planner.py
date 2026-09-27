"""V2-08b runtime demo: chase plan, fill, missed chase. Paper only. No secrets."""

from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path

from brokers.fills import ClockedPaperBroker, Quote
from contracts.clock import SimClock
from helpers import INST, NOW, make_decision, make_router

from oms.planner import (
    REPO_CHASE_YAML,
    REPO_ENTRY_YAML,
    CardPolicy,
    EntryConfigStore,
    OrderPlanner,
    load_entry_location,
    marketable_limit,
    resolve_policy,
)


def _quote(ask: float) -> Quote:
    return Quote(
        available_ts=NOW,
        bid=ask - 0.10,
        ask=ask,
        ltp=ask,
        instrument_id=INST,
    )


def main() -> None:
    cfg = load_entry_location()
    policy = resolve_policy(cfg)
    print(f"config_hash={cfg.config_hash}")
    print(f"chase_calibration={policy.chase_calibration}")
    print(f"mode={policy.mode} ticks={policy.max_chase_ticks} timeout={policy.chase_timeout_s}")
    print(f"params_hash={policy.params_hash}")
    over = resolve_policy(cfg, CardPolicy(max_chase_ticks=5))
    print(f"override_params_hash={over.params_hash} changed={over.params_hash != policy.params_hash}")

    clock = SimClock(NOW)
    broker = ClockedPaperBroker(clock=clock)
    tmp = Path(tempfile.mkdtemp(prefix="v2-08b-demo-"))
    router = make_router(tmp, clock, broker=broker)
    planner = OrderPlanner(
        clock=clock,
        router=router,
        config_store=EntryConfigStore(REPO_ENTRY_YAML, chase_path=REPO_CHASE_YAML),
    )
    ask = 151.35
    plan = planner.accept(make_decision(), bar_close_ts=NOW - timedelta(seconds=1))
    assert plan is not None
    print(f"ENTRY_PLAN action={plan.action} limit={plan.limit_price} oid={plan.client_order_id}")
    planner.on_quote(_quote(ask))
    live = planner.plan(plan.signal_id)
    assert live is not None
    print(f"sent limit={live.plan.limit_price} expected={marketable_limit(ask, 2)} status={live.status}")
    if live.result is not None:
        print(f"ENTRY_PLAN_RESULT status={live.result.status} fill={live.result.fill_price}")
    print("demo_ok")


if __name__ == "__main__":
    main()
