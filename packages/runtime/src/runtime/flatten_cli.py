"""python -m runtime flatten — out-of-band paper flatten. No Redis. No DhanBroker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from control.flatten import flatten_paper, paper_broker
from oms import MemoryLedger, OrderRouter, PositionManager  # type: ignore[import-untyped]
from risk_engine import V2RiskEngine  # type: ignore[import-untyped]


def flatten_cli(*, account: str, state_dir: Path, clock: Any, manager: Any | None = None) -> dict[str, Any]:
    if manager is not None:
        return flatten_paper(account=account, clock=clock, risk=manager.router.risk, manager=manager)
    cfg_src = Path("config/risk_limits.yaml")
    raw = yaml.safe_load(cfg_src.read_text(encoding="utf-8")) if cfg_src.is_file() else {}
    raw = dict(raw or {})
    raw["kill_switch_file"] = str(state_dir / "KILL_SWITCH")
    risk_path = state_dir / "risk_limits.yaml"
    risk_path.parent.mkdir(parents=True, exist_ok=True)
    risk_path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    store = MemoryLedger()
    broker = paper_broker(clock)
    risk = V2RiskEngine(ledger=store, config_path=risk_path, root=state_dir)
    router = OrderRouter(clock=clock, risk=risk, broker=broker, store=store)
    desk = PositionManager(clock=clock, router=router, store=store)
    return flatten_paper(account=account, clock=clock, risk=risk, manager=desk)
