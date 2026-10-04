"""Preregistered forward specs and lock (REG-13b). Posted win rates are not a field."""

from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from strategies.params_hash import compute_params_hash

FORBIDDEN_FIELDS = frozenset({"win_rate", "winrate", "posted_win_rate"})


class SpecError(ValueError):
    """Spec YAML is missing, malformed, or uses a forbidden field."""


class SpecRefused(ValueError):
    """Spec hash does not match prereg.lock (or exit params drifted)."""


@dataclass(frozen=True)
class ForwardSpec:
    spec_id: str
    strategy_id: str
    plugin: str
    params: dict[str, Any]
    coefficients: dict[str, Any]
    bars: dict[str, Any]
    placebos: tuple[str, ...]
    start_session: str
    cost_model: str
    stage: str
    signals: tuple[dict[str, Any], ...]
    raw: dict[str, Any]


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def plugin_source(module_path: str) -> str:
    mod = importlib.import_module(module_path)
    src = getattr(mod, "__file__", None)
    if not src:
        raise SpecError(f"plugin {module_path} has no source file")
    return Path(src).read_text(encoding="utf-8")


def compute_lock_digest(
    spec_raw: dict[str, Any],
    plugin_src: str,
    coefficients: dict[str, Any] | None = None,
) -> str:
    """sha256(canonical spec + plugin source + coefficients)."""
    blob = _canonical(spec_raw) + plugin_src + _canonical(coefficients or {})
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def exit_params_hash(params: dict[str, Any]) -> str:
    return compute_params_hash({"exit_plan": params.get("exit_plan") or {}})


def load_spec(path: Path) -> ForwardSpec:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SpecError("spec must be a mapping")
    banned = FORBIDDEN_FIELDS.intersection(loaded) | FORBIDDEN_FIELDS.intersection(
        loaded.get("params") or {}
    )
    if banned:
        raise SpecError(f"posted win rates are not an input field: {sorted(banned)}")
    for key in ("spec_id", "strategy_id", "plugin", "params"):
        if key not in loaded:
            raise SpecError(f"spec missing {key}")
    params = dict(loaded["params"] or {})
    if "exit_plan" not in params:
        raise SpecError("params.exit_plan is required (REG-13)")
    return ForwardSpec(
        spec_id=str(loaded["spec_id"]),
        strategy_id=str(loaded["strategy_id"]),
        plugin=str(loaded["plugin"]),
        params=params,
        coefficients=dict(loaded.get("coefficients") or {}),
        bars=dict(loaded.get("bars") or {}),
        placebos=tuple(loaded.get("placebos") or ("side_flip", "random_minute")),
        start_session=str(loaded.get("start_session") or ""),
        cost_model=str(loaded.get("cost_model") or "depth"),
        stage=str(loaded.get("stage") or "shadow"),
        signals=tuple(loaded.get("signals") or ()),
        raw=loaded,
    )


def load_lock(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SpecRefused(f"prereg.lock missing: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SpecRefused("prereg.lock must be a mapping")
    return loaded


def verify_lock(spec: ForwardSpec, lock: dict[str, Any]) -> str:
    """Refuse when spec+plugin+coefficients or exit params differ from the lock."""
    rows = lock.get("specs") if isinstance(lock.get("specs"), dict) else lock
    row = rows.get(spec.spec_id) if isinstance(rows, dict) else None
    if not isinstance(row, dict) or "sha256" not in row:
        raise SpecRefused(f"spec {spec.spec_id} is not in prereg.lock")
    digest = compute_lock_digest(spec.raw, plugin_source(spec.plugin), spec.coefficients)
    if digest != str(row["sha256"]):
        raise SpecRefused(f"spec hash mismatch for {spec.spec_id}")
    locked_exit = str(row.get("exit_sha256") or "")
    if locked_exit and locked_exit != exit_params_hash(spec.params):
        raise SpecRefused(f"REG-13b: exit params differ from prereg lock for {spec.spec_id}")
    return digest
