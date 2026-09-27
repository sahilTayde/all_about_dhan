"""Paper-only fixtures for V2-11. Writes only under tmp_path."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from contracts.ids import order_id
from contracts.payloads import CatastrophicStop, Decision, EntryPlan, ExitPlan, Level
from oms import Account, OrderRouter, PositionManager, Veto
from risk_engine import IST, V2RiskEngine

from control.handler import ControlHandler
from control.store import MemoryCommandStore

NOW = datetime(2026, 9, 28, 10, 1, tzinfo=IST)
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
SIG = "sg_ctrl_nifty_20260928_1001_0"
REPO = Path(__file__).resolve().parents[3]


def write_risk_cfg(tmp_path: Path, **overrides: Any) -> Path:
    cfg = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())
    cfg.update(overrides)
    cfg["kill_switch_file"] = str(tmp_path / "KILL_SWITCH")
    path = tmp_path / "risk_limits.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def make_plan(**kw: Any) -> EntryPlan:
    data = dict(
        plan_id="ep_1",
        decision_id="dc_1",
        signal_id=SIG,
        account_id="founder",
        action="CHASE",
        shadow_actions=[],
        stretch={"zone_atr": 1.0, "ema20_atr": 1.0, "twap_atr": 1.0, "catastrophic_price": 140.0},
        zone="fvg",
        zone_price=24500.0,
        entry_distance_atr=1.0,
        signal_candle_atr=1.0,
        limit_price=151.40,
        est_delta=0.66,
        expires_at="2026-09-28T10:04:01+05:30",
        client_order_id=order_id("founder", SIG, "entry"),
    )
    data.update(kw)
    return EntryPlan(**data)


def make_decision(**kw: Any) -> Decision:
    data = dict(
        decision_id="dc_1",
        underlying="NIFTY",
        decision="ENTER",
        signal_ids=[SIG],
        instrument_id=INST,
        lots=1,
        lot_size=65,
        limit_price=151.40,
        shadow={"chosen": "ITM100"},
    )
    data.update(kw)
    return Decision(**data)


def make_exit_plan(**kw: Any) -> ExitPlan:
    data: dict[str, Any] = dict(
        catastrophic=CatastrophicStop(level=Level(kind="premium", price=140.0)),
        time_stops=(),
        flat_by_ist="15:15",
    )
    data.update(kw)
    return ExitPlan(**data)


def make_router(tmp_path: Path, clock: SimClock, **kw: Any) -> OrderRouter:
    from oms import MemoryLedger

    store = kw.pop("store", MemoryLedger())
    risk = kw.pop("risk", None)
    if risk is None:
        risk = V2RiskEngine(ledger=store, config_path=write_risk_cfg(tmp_path), root=tmp_path)
    broker = kw.pop("broker", None) or make_broker(clock=clock)
    return OrderRouter(clock=clock, risk=risk, broker=broker, store=store, **kw)


def fill_entry(router: OrderRouter, clock: SimClock, inst: str = INST) -> None:
    clock.advance_by(timedelta(milliseconds=250))
    router.broker.on_depth(Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=inst))


def open_one(tmp_path: Path, clock: SimClock | None = None) -> tuple[PositionManager, SimClock]:
    clock = clock or SimClock(NOW)
    pm = PositionManager(clock=clock, router=make_router(tmp_path, clock))
    out = pm.router.submit(make_plan(), make_decision(), Account("founder"), exit_plan=make_exit_plan())
    assert not isinstance(out, Veto)
    fill_entry(pm.router, clock)
    assert pm.open_book()
    return pm, clock


def make_handler(tmp_path: Path, clock: SimClock | None = None, **kw: Any) -> ControlHandler:
    clock = clock or SimClock(NOW)
    manager = kw.pop("manager", None)
    return ControlHandler(
        store=kw.pop("store", MemoryCommandStore()),
        root=tmp_path,
        clock=clock,
        manager=manager,
        risk=kw.pop("risk", manager.router.risk if manager is not None else None),
        kill_switch_path=tmp_path / "KILL_SWITCH",
        bus=kw.pop("bus", None),
        **kw,
    )
