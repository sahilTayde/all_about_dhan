"""
Strategy registry and basket loader (V2-06).

This is a YAML-based fallback implementation until the real registry/basket
module is built separately. The runtime depends only on these contracts:

    load_registry() -> dict[str, RegistryEntry]
    load_basket(session, market) -> Basket

NO BASKET MEANS NO TRADES (fail closed).
"""

import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RegistryEntry:
    """
    Strategy registry entry.

    Maps strategy_id to module path, version, params_hash, and stage.
    """

    strategy_id: str
    module_path: str  # e.g. "strategies.plugins.test_cross"
    version: str
    params_hash: str
    stage: str  # "shadow" | "paper" | "live_eligible"


@dataclass(frozen=True)
class BasketEntry:
    """
    Single strategy in the daily basket.

    The boss will only consider signals from strategies in the active basket.
    """

    strategy_id: str
    underlyings: tuple[str, ...]  # ("NIFTY", "SENSEX")
    weight: float  # relative weight for position sizing
    max_lots: int  # per-strategy lot cap
    stage: str  # can downgrade from registry (e.g. shadow override)


@dataclass(frozen=True)
class Basket:
    """
    Daily basket configuration.

    Loaded per session and frozen for the day. Founder commands can only
    remove entries mid-session, not add them.
    """

    session: str  # YYYY-MM-DD
    market: str  # "IN_INDEX_OPT"
    entries: tuple[BasketEntry, ...]
    source: str  # "yaml" | "registry_module" (when real module lands)
    basket_hash: str  # sha256 of canonical basket config


def load_registry(config_path: Path | None = None) -> dict[str, RegistryEntry]:
    """
    Load strategy registry from YAML.

    Args:
        config_path: Path to registry.yaml (default: config/v2/strategies/registry.yaml)

    Returns:
        Dict mapping strategy_id to RegistryEntry

    Raises:
        FileNotFoundError: If registry file doesn't exist
        ValueError: If registry YAML is invalid

    The YAML format:
        strategies:
          - strategy_id: "TEST-CROSS"
            module_path: "strategies.plugins.test_cross"
            version: "1.0.0"
            params_hash: "abc123..."
            stage: "shadow"
    """
    if config_path is None:
        config_path = Path("config/v2/strategies/registry.yaml")

    if not config_path.exists():
        warnings.warn(
            f"Registry file not found: {config_path}. "
            "Using empty registry (no strategies loaded).",
            stacklevel=2,
        )
        return {}

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not data or "strategies" not in data:
        return {}

    registry = {}
    for entry_dict in data["strategies"]:
        entry = RegistryEntry(
            strategy_id=entry_dict["strategy_id"],
            module_path=entry_dict["module_path"],
            version=entry_dict["version"],
            params_hash=entry_dict["params_hash"],
            stage=entry_dict["stage"],
        )
        registry[entry.strategy_id] = entry

    return registry


def load_basket(session: date, market: str, config_dir: Path | None = None) -> Basket | None:
    """
    Load daily basket from YAML.

    Args:
        session: Trading session date
        market: Market name (e.g. "IN_INDEX_OPT")
        config_dir: Config directory (default: config/v2/baskets)

    Returns:
        Basket if file exists and valid, None otherwise

    NO BASKET MEANS NO TRADES (fail closed). The runtime will publish
    a health alert if the basket is missing.

    The YAML format:
        session: "2026-09-27"
        market: "IN_INDEX_OPT"
        entries:
          - strategy_id: "TEST-CROSS"
            underlyings: ["NIFTY"]
            weight: 1.0
            max_lots: 10
            stage: "shadow"
    """
    if config_dir is None:
        config_dir = Path("config/v2/baskets")

    session_str = session.strftime("%Y-%m-%d")
    basket_path = config_dir / f"{session_str}.yaml"

    if not basket_path.exists():
        warnings.warn(
            f"Basket file not found for {session_str} at {basket_path}. "
            "NO BASKET MEANS NO TRADES (fail closed).",
            stacklevel=2,
        )
        return None

    try:
        with open(basket_path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        warnings.warn(
            f"Failed to load basket from {basket_path}: {e}. "
            "NO BASKET MEANS NO TRADES (fail closed).",
            stacklevel=2,
        )
        return None

    if not data:
        return None

    # Validate session matches
    if data.get("session") != session_str:
        warnings.warn(
            f"Basket session mismatch: file {session_str}, content {data.get('session')}",
            stacklevel=2,
        )
        return None

    if data.get("market") != market:
        warnings.warn(
            f"Basket market mismatch: requested {market}, file has {data.get('market')}",
            stacklevel=2,
        )
        return None

    entries = []
    for entry_dict in data.get("entries", []):
        entries.append(
            BasketEntry(
                strategy_id=entry_dict["strategy_id"],
                underlyings=tuple(entry_dict["underlyings"]),
                weight=float(entry_dict["weight"]),
                max_lots=int(entry_dict["max_lots"]),
                stage=entry_dict["stage"],
            )
        )

    import hashlib
    import json

    basket_dict = {
        "session": session_str,
        "market": market,
        "entries": [
            {
                "strategy_id": e.strategy_id,
                "underlyings": list(e.underlyings),
                "weight": e.weight,
                "max_lots": e.max_lots,
                "stage": e.stage,
            }
            for e in entries
        ],
    }
    basket_json = json.dumps(basket_dict, sort_keys=True, separators=(",", ":"))
    basket_hash = hashlib.sha256(basket_json.encode()).hexdigest()[:16]

    return Basket(
        session=session_str,
        market=market,
        entries=tuple(entries),
        source="yaml",
        basket_hash=basket_hash,
    )
