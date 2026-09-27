"""Shared paper-only fixtures for V2-08 tests. Writes only under tmp_path."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from contracts.ids import order_id
from contracts.payloads import Decision, EntryPlan
from events.bus import MemoryBus
from risk_engine import IST, V2RiskEngine

from brokers.fills import ClockedPaperBroker, Quote

from oms import MemoryLedger, OrderRouter

NOW = datetime(2026, 9, 28, 10, 1, tzinfo=IST)
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
SIG = "sg_test_nifty_20260928_1001_0"
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
        lots=2,
        lot_size=65,
        limit_price=151.40,
        shadow={"chosen": "ITM100"},
    )
    data.update(kw)
    return Decision(**data)


class NoFillBroker(ClockedPaperBroker):
    """Records quotes but never fills (timeout / restart paths)."""

    def on_depth(self, quote: Quote) -> None:
        if quote.available_ts <= self.clock.now():
            self.quotes.append(quote)


class SpyBroker(NoFillBroker):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.place_calls = 0
        self.types: list[str] = []

    def place_order(self, intent: object, decision: object) -> object:
        self.place_calls += 1
        self.types.append(str(getattr(intent, "order_type", "")))
        return super().place_order(intent, decision)  # type: ignore[arg-type]


def quote_at(
    now: datetime, ask: float, bid: float | None = None, ltp: float | None = None
) -> Quote:
    return Quote(
        available_ts=now,
        bid=bid if bid is not None else ask - 0.10,
        ask=ask,
        ltp=ltp if ltp is not None else ask,
        instrument_id=INST,
    )


def write_entry_cfg(tmp_path: Path, **overrides: Any) -> Path:
    cfg = yaml.safe_load((REPO / "config" / "v2" / "entry_location.yaml").read_text())
    cfg.update(overrides)
    path = tmp_path / "entry_location.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return path


def make_router(tmp_path: Path, clock: Any, **kw: Any) -> OrderRouter:
    store: MemoryLedger = kw.pop("store", MemoryLedger())
    bus: MemoryBus = kw.pop("bus", MemoryBus())
    risk = kw.pop("risk", None)
    if risk is None:
        risk = V2RiskEngine(ledger=store, config_path=write_risk_cfg(tmp_path), bus=bus)
    return OrderRouter(clock=clock, risk=risk, store=store, bus=bus, **kw)
