"""Shared desk risk gate (paper). Config: config/desk_risk.yaml. No broker.

One gate for every desk entry path. `check()` decides one entry at minute `t` against the desk
positions already taken; `state()` is the board.risk summary the website reads (same numbers).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

RISK_CAP_TRADES = "RISK_CAP_TRADES"
RISK_CAP_OPEN = "RISK_CAP_OPEN"
RISK_DAY_STOP = "RISK_DAY_STOP"
RISK_STATUSES = (RISK_CAP_TRADES, RISK_CAP_OPEN, RISK_DAY_STOP)

CONFIG_PATH = Path(__file__).resolve().parents[4] / "config" / "desk_risk.yaml"
DEFAULTS: dict[str, Any] = {
    "max_trades_per_day": None,
    "max_open": 2,
    "day_stop_losers": 2,
    "day_stop_net_inr": -25000.0,
    "group_stop": {"rule_ids": ["R01_PDIV_5_ALL_H20", "R01_B3A_VOL"], "net_inr": -15000.0},
}
_IST = timezone(timedelta(hours=5, minutes=30))


def load_config(path: Optional[Path] = None) -> dict[str, Any]:
    cfg = json.loads(json.dumps(DEFAULTS))
    p = Path(path) if path is not None else CONFIG_PATH
    if p.is_file():
        import yaml

        blob = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(blob, dict):
            raise ValueError(f"{p}: expected a mapping")
        cfg.update(blob)
    return cfg


def _end(k: dict[str, Any]) -> str:
    return max(str(k.get("exit_min") or "99:99"), str(k.get("spec_exit_min") or ""))


def holds_at(k: dict[str, Any], k_open: bool, t: str) -> bool:
    ks = str(k.get("entry_min") or "")
    return ks <= t if k_open else ks <= t <= _end(k)


def _net(k: dict[str, Any]) -> float:
    v = k.get("realized_pnl_inr")
    return float(v) if isinstance(v, (int, float)) else 0.0


def _realized(taken: Iterable[tuple[dict[str, Any], bool]], t: Optional[str]) -> list[dict[str, Any]]:
    """Closed desk trades whose exit was done before minute t (t=None: all closed)."""
    return [k for k, o in taken if not o and (t is None or _end(k) < t)]


def _stop_reason(done: list[dict[str, Any]], rule_id: Optional[str], cfg: dict[str, Any]) -> Optional[str]:
    losers = sum(1 for k in done if _net(k) < 0)
    if cfg.get("day_stop_losers") is not None and losers >= int(cfg["day_stop_losers"]):
        return RISK_DAY_STOP
    if cfg.get("day_stop_net_inr") is not None and sum(_net(k) for k in done) <= float(cfg["day_stop_net_inr"]):
        return RISK_DAY_STOP
    grp = cfg.get("group_stop") or {}
    ids = set(grp.get("rule_ids") or [])
    if rule_id is not None and rule_id in ids and grp.get("net_inr") is not None:
        if sum(_net(k) for k in done if k.get("rule_id") in ids) <= float(grp["net_inr"]):
            return RISK_DAY_STOP
    return None


def check(taken: list[tuple[dict[str, Any], bool]], r: dict[str, Any], cfg: dict[str, Any]) -> Optional[str]:
    """None = entry allowed; else the RISK_* status. `taken` = desk positions (row, is_open) so far."""
    t = str(r.get("entry_min") or "")
    stop = _stop_reason(_realized(taken, t), r.get("rule_id"), cfg)
    if stop:
        return stop
    cap = cfg.get("max_trades_per_day")
    if cap is not None and len(taken) >= int(cap):
        return RISK_CAP_TRADES
    if cfg.get("max_open") is not None and sum(1 for k, o in taken if holds_at(k, o, t)) >= int(cfg["max_open"]):
        return RISK_CAP_OPEN
    return None


def state(taken: list[tuple[dict[str, Any], bool]], cfg: dict[str, Any]) -> dict[str, Any]:
    """board.risk: the same counts the gate uses."""
    done = _realized(taken, None)
    ids = set((cfg.get("group_stop") or {}).get("rule_ids") or [])
    open_now = sum(1 for _, o in taken if o)
    stop = _stop_reason(done, None, cfg)
    grp_net = round(sum(_net(k) for k in done if k.get("rule_id") in ids), 2)
    grp_hit = bool(ids) and (cfg.get("group_stop") or {}).get("net_inr") is not None and grp_net <= float(cfg["group_stop"]["net_inr"])
    cap = cfg.get("max_trades_per_day")
    halted = stop or (RISK_CAP_TRADES if cap is not None and len(taken) >= int(cap) else None) or (
        RISK_CAP_OPEN if cfg.get("max_open") is not None and open_now >= int(cfg["max_open"]) else None)
    return {
        "trades_today": len(taken),
        "max_trades": cap,
        "open_now": open_now,
        "max_open": cfg.get("max_open"),
        "losers_today": sum(1 for k in done if _net(k) < 0),
        "day_net_inr": round(sum(_net(k) for k in done), 2),
        "day_stop_hit": stop is not None,
        "rr_group_net_inr": grp_net,
        "rr_group_stop_hit": bool(grp_hit),
        "halted_reason": halted,
        "config": {k: cfg.get(k) for k in ("max_trades_per_day", "max_open", "day_stop_losers", "day_stop_net_inr", "group_stop")},
    }


def live_entry_block(root: Path, day: Optional[str] = None, environ: Optional[dict[str, str]] = None) -> Optional[str]:
    """For non-research desk paths (paper_scalp _try_open): halted_reason from the published research
    journal's risk block. Only when DESK_RISK_GATE_LIVE=1 (set by scripts/desk.sh), so replays and
    golden tests are unaffected."""
    env = os.environ if environ is None else environ
    if str(env.get("DESK_RISK_GATE_LIVE", "")).strip() not in {"1", "true", "yes", "on"}:
        return None
    day = day or datetime.now(_IST).date().isoformat()
    try:
        blob = json.loads((Path(root) / "data" / "recon" / "research_rules" / f"{day}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    risk = blob.get("risk") if isinstance(blob, dict) else None
    return (risk or {}).get("halted_reason") if isinstance(risk, dict) else None
