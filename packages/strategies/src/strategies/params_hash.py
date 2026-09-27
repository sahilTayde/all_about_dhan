"""
Parameter hashing for strategy preregistration (REG-13).

The params_hash covers ALL parameters including:
- Strategy coefficients/weights
- Exit plan (all fields)
- Time stops
- Strike router rules (via rule_version in StrikeChoice)

REG-13a: Changing any exit field changes params_hash and config_hash.
"""

import hashlib
import json
from typing import Any

from .api import ExitPlan, Level, Partial, TimeStop, Trail


def compute_params_hash(params: dict[str, Any]) -> str:
    """
    Compute deterministic SHA-256 hash of strategy parameters.

    Args:
        params: Dictionary of all strategy parameters, including:
            - Coefficients/weights
            - exit_plan (ExitPlan or dict)
            - strike_router_rules (if applicable)
            - Any other strategy-specific config

    Returns:
        First 16 chars of hex SHA-256 hash

    The hash is stable across processes and deterministic on the canonical
    JSON representation (sorted keys, no whitespace).
    """
    canonical = _canonicalize(params)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:16]  # 16 hex chars = 64 bits


def _canonicalize(obj: Any) -> str:
    """
    Convert object to canonical JSON string for hashing.

    Handles dataclasses by converting them to dicts first.
    Sorts all dict keys recursively for stability.
    """
    return json.dumps(_to_dict(obj), sort_keys=True, separators=(",", ":"))


def _to_dict(obj: Any) -> Any:
    """
    Recursively convert dataclasses and enums to JSON-serializable dicts.

    This ensures that ExitPlan, TimeStop, Level etc. are hashed correctly.
    """
    if hasattr(obj, "__dataclass_fields__"):
        # Dataclass: convert to dict
        return {
            field: _to_dict(getattr(obj, field))
            for field in obj.__dataclass_fields__
        }
    elif isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_to_dict(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        # Fallback: convert to string
        return str(obj)


def exit_plan_hash(plan: ExitPlan) -> str:
    """
    Compute hash of just the exit plan.

    This is a convenience for checking REG-13a: changing any exit field
    must change the hash.
    """
    return compute_params_hash({"exit_plan": plan})