"""Opt-in recommended playbook as a V2 ExitPlan mapping. OFF unless enabled."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

PLAYBOOK_RELATIVE = Path("config/v2/exits/exitlab_playbook.yaml")


def load_playbook_yaml(path: Path | None = None) -> dict[str, Any]:
    target = path if path is not None else PLAYBOOK_RELATIVE
    raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("exitlab playbook must be a mapping")
    return raw


def playbook_enabled(raw: dict[str, Any] | None = None, *, env_flag: str | None = None) -> bool:
    """OFF unless yaml enabled:true AND env EXITLAB_PLAYBOOK=1 (or explicit env_flag)."""
    blob = raw if raw is not None else {}
    yaml_on = bool(blob.get("enabled"))
    env_on = (env_flag or "") in {"1", "true", "TRUE", "yes"}
    return yaml_on and env_on


def playbook_to_exit_plan_mapping(raw: dict[str, Any]) -> dict[str, Any]:
    """Compile research playbook into existing V2 ExitPlan fields only."""
    rec = raw.get("recommended") or {}
    cat = rec.get("catastrophic") or {"max_loss_inr": 8000}
    mapping: dict[str, Any] = {
        "catastrophic": {
            "level": {
                "kind": "max_loss_inr",
                "price": float(cat.get("max_loss_inr", 8000)),
            }
        },
        "flat_by_ist": str(rec.get("flat_by_ist") or "15:15"),
        "defaults_from": "exitlab_playbook",
    }
    if rec.get("time_stop_s"):
        mapping["time_stops"] = [
            {
                "after_s": int(rec["time_stop_s"]),
                "when": "always",
                "unless_profit_pts": rec.get("unless_profit_pts"),
            }
        ]
    if rec.get("target_premium"):
        mapping["target"] = {"kind": "premium", "price": float(rec["target_premium"])}
    if rec.get("trail"):
        tr = rec["trail"]
        mapping["trail"] = {
            "kind": str(tr.get("kind") or "step"),
            "activate_at": {"kind": "premium", "price": float(tr.get("activate", 0))},
            "step": tr.get("step"),
            "percent": tr.get("percent"),
        }
    if rec.get("grace_s"):
        mapping["grace"] = {"seconds": int(rec["grace_s"])}
    if rec.get("partials"):
        mapping["partials"] = rec["partials"]
    return mapping
