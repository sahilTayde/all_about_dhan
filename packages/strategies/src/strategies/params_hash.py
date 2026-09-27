"""Parameter and config hashing (REG-13).

`params_hash` covers every strategy param including the exit plan, time stops
and strike-router rules. `config_hash` covers shared YAML (exit defaults,
router rules). Changing any exit field changes both hashes (REG-13a).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from contracts.payloads import (
    CatastrophicStop,
    ExitPlan,
    Level,
    StructuralStop,
)

# sha256 of origin/main:config/v2/exits/defaults.yaml (round 11). Do not vendor the file.
ROUND11_DEFAULTS_SHA256 = "d8b2b6e5f75367697afcac5fa86ac76783c794c6486f17a739e2e8335662dd14"
DEFAULTS_RELATIVE = Path("config/v2/exits/defaults.yaml")


class ExitPlanLoadError(ValueError):
    """REG-18d: a plan without a catastrophic stop must refuse to load."""


def compute_params_hash(params: dict[str, Any]) -> str:
    """First 16 hex chars of SHA-256 over canonical JSON (sorted keys)."""
    digest = hashlib.sha256(_canonicalize(params).encode("utf-8")).hexdigest()
    return digest[:16]


def config_hash(
    *,
    exit_defaults: dict[str, Any] | None = None,
    router_rules: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Hash of shared engine config (defaults + router rules + extras)."""
    return compute_params_hash(
        {
            "exit_defaults": exit_defaults or {},
            "router_rules": router_rules or {},
            "extra": extra or {},
        }
    )


def exit_plan_hash(plan: ExitPlan) -> str:
    """Hash of one exit plan (REG-13a)."""
    return compute_params_hash({"exit_plan": plan})


def defaults_from_tag(file_sha256: str) -> str:
    """`defaults_from` value frozen into a plan (K18 / REG-13)."""
    return f"exit_defaults@{file_sha256}"


def load_exit_defaults(path: Path | None = None) -> tuple[dict[str, Any], str]:
    """Load `config/v2/exits/defaults.yaml` as it exists on disk (main's file).

    This package does not vendor the YAML. Callers pass the repo path or a
    test copy. Returns (parsed mapping, sha256 of the raw file bytes).
    """
    import yaml  # type: ignore[import-untyped]

    target = path if path is not None else DEFAULTS_RELATIVE
    raw = target.read_bytes()
    loaded = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(loaded, dict):
        raise ExitPlanLoadError("exit defaults YAML must be a mapping")
    digest = hashlib.sha256(raw).hexdigest()
    return loaded, digest


def resolve_exit_plan(
    overrides: dict[str, Any] | None = None,
    *,
    defaults: dict[str, Any] | None = None,
    defaults_sha256: str | None = None,
) -> ExitPlan:
    """Build an ExitPlan from overrides + optional round-11 defaults.

    REG-18d: refuse if neither the plan nor the defaults supply a catastrophic
    stop. Structural has no default level (defaults.yaml `structural.enabled`);
    a strategy that wants one must declare it.
    """
    data = dict(overrides or {})
    inherited = False
    catastrophic = _catastrophic_from(data.get("catastrophic"))
    if catastrophic is None and defaults is not None:
        catastrophic = _catastrophic_from_defaults(defaults)
        inherited = catastrophic is not None
    if catastrophic is None:
        raise ExitPlanLoadError("REG-18d: a plan without a catastrophic stop refuses to load")

    structural = _structural_from(data.get("structural"))
    tag = None
    if inherited and defaults_sha256:
        tag = defaults_from_tag(defaults_sha256)
    elif isinstance(data.get("defaults_from"), str):
        tag = str(data["defaults_from"])

    return ExitPlan(
        catastrophic=catastrophic,
        structural=structural,
        atr=None,
        time_stops=tuple(data.get("time_stops") or ()),
        grace=None,
        signal_flip=None,
        target=data.get("target"),
        partials=tuple(data.get("partials") or ()),
        trail=data.get("trail"),
        flat_by_ist=str(data.get("flat_by_ist") or "15:15"),
        defaults_from=tag,
    )


def _catastrophic_from(raw: object) -> CatastrophicStop | None:
    if raw is None:
        return None
    if isinstance(raw, CatastrophicStop):
        return raw
    if isinstance(raw, dict):
        if "level" in raw and isinstance(raw["level"], dict):
            level = raw["level"]
            return CatastrophicStop(
                level=Level(kind=str(level["kind"]), price=float(level["price"]))
            )
        if "max_loss" in raw:
            return CatastrophicStop(level=Level(kind="premium", price=float(raw["max_loss"])))
        if "level" in raw and isinstance(raw["level"], Level):
            return CatastrophicStop(level=raw["level"])
    return None


def _catastrophic_from_defaults(defaults: dict[str, Any]) -> CatastrophicStop | None:
    block = defaults.get("catastrophic")
    if not isinstance(block, dict):
        return None
    if "max_loss" not in block:
        return None
    return CatastrophicStop(level=Level(kind="premium", price=float(block["max_loss"])))


def _structural_from(raw: object) -> StructuralStop | None:
    if raw is None:
        return None
    if isinstance(raw, StructuralStop):
        return raw
    if isinstance(raw, dict) and "level" in raw:
        level = raw["level"]
        if isinstance(level, Level):
            return StructuralStop(level=level, trigger=str(raw.get("trigger") or "bar_close"))
        if isinstance(level, dict):
            return StructuralStop(
                level=Level(kind=str(level["kind"]), price=float(level["price"])),
                trigger=str(raw.get("trigger") or "bar_close"),
            )
    return None


def _canonicalize(obj: object) -> str:
    return json.dumps(_to_dict(obj), sort_keys=True, separators=(",", ":"))


def _to_dict(obj: object) -> object:
    if hasattr(obj, "__dataclass_fields__"):
        return {name: _to_dict(getattr(obj, name)) for name in obj.__dataclass_fields__}
    if isinstance(obj, dict):
        return {str(k): _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(item) for item in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)
