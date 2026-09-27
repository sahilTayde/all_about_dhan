"""Strategy registry and daily basket (V2-06).

YAML fallback plus a read-only adapter for the basket track's
`basket_india.json` / `basket_forex.json` (decision K6). No basket means
no trades (fail closed).
"""

from __future__ import annotations

import hashlib
import json
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

INDIA_MARKET = "IN_INDEX_OPT"
FOREX_MARKET = "FX_SPOT"


@dataclass(frozen=True)
class RegistryEntry:
    """strategy_id -> module path, version, params_hash, stage."""

    strategy_id: str
    module_path: str
    version: str
    params_hash: str
    stage: str
    legacy_logic_from: tuple[str, ...] = ()


@dataclass(frozen=True)
class BasketEntry:
    """One strategy in the session basket."""

    strategy_id: str
    underlyings: tuple[str, ...]
    weight: float
    max_lots: int
    stage: str


@dataclass(frozen=True)
class Basket:
    """Frozen daily basket. Founder commands may remove entries, not add."""

    session: str
    market: str
    entries: tuple[BasketEntry, ...]
    source: str
    basket_hash: str


def load_registry(config_path: Path | None = None) -> dict[str, RegistryEntry]:
    """Load `config/v2/strategies/registry.yaml`. Missing file → empty registry."""
    import yaml  # type: ignore[import-untyped]

    path = config_path if config_path is not None else Path("config/v2/strategies/registry.yaml")
    if not path.exists():
        warnings.warn(
            f"Registry file not found: {path}. Using empty registry (no strategies loaded).",
            stacklevel=2,
        )
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data or "strategies" not in data:
        return {}
    registry: dict[str, RegistryEntry] = {}
    for entry_dict in data["strategies"]:
        legacy = entry_dict.get("legacy_logic_from") or []
        entry = RegistryEntry(
            strategy_id=entry_dict["strategy_id"],
            module_path=entry_dict["module_path"],
            version=entry_dict["version"],
            params_hash=entry_dict["params_hash"],
            stage=entry_dict["stage"],
            legacy_logic_from=tuple(legacy),
        )
        registry[entry.strategy_id] = entry
    return registry


def load_basket(
    session: date,
    market: str,
    config_dir: Path | None = None,
    json_path: Path | None = None,
) -> Basket | None:
    """Load the daily basket. YAML dated file first, then K6 JSON adapter.

    Returns None when nothing is found (NO TRADES, fail closed).
    """
    directory = config_dir if config_dir is not None else Path("config/v2/baskets")
    session_str = session.strftime("%Y-%m-%d")
    yaml_path = directory / f"{session_str}.yaml"
    if yaml_path.exists():
        basket = _load_basket_yaml(yaml_path, session_str, market)
        if basket is not None:
            return basket
    adapted = load_basket_json(session, market, json_path=json_path, config_dir=directory)
    if adapted is not None:
        return adapted
    warnings.warn(
        f"Basket file not found for {session_str} at {yaml_path}. "
        "NO BASKET MEANS NO TRADES (fail closed).",
        stacklevel=2,
    )
    return None


def basket_for(session: date, market: str, config_dir: Path | None = None) -> Basket | None:
    """Architecture §2.5 contract name for `load_basket`."""
    return load_basket(session, market, config_dir=config_dir)


def load_basket_json(
    session: date,
    market: str,
    *,
    json_path: Path | None = None,
    config_dir: Path | None = None,
) -> Basket | None:
    """Read-only adapter for `basket_india.json` / `basket_forex.json` (K6)."""
    directory = config_dir if config_dir is not None else Path("config/v2/baskets")
    if json_path is None:
        name = "basket_india.json" if market == INDIA_MARKET else "basket_forex.json"
        json_path = directory / name
    if not json_path.is_file():
        return None
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"Failed to read basket JSON {json_path}: {exc}", stacklevel=2)
        return None
    if not isinstance(data, dict):
        return None
    file_market = data.get("market")
    if file_market is not None and file_market != market:
        return None
    session_str = session.strftime("%Y-%m-%d")
    file_session = data.get("session")
    if file_session is not None and file_session != session_str:
        return None
    raw_entries = data.get("entries") or data.get("cards") or []
    entries = tuple(_entry_from_mapping(item) for item in raw_entries if isinstance(item, dict))
    return _basket(session_str, market, entries, source=f"json:{json_path.name}")


def _load_basket_yaml(path: Path, session_str: str, market: str) -> Basket | None:
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings.warn(
            f"Failed to load basket from {path}: {exc}. NO BASKET MEANS NO TRADES (fail closed).",
            stacklevel=2,
        )
        return None
    if not data:
        return None
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
    entries = tuple(_entry_from_mapping(item) for item in data.get("entries") or [])
    return _basket(session_str, market, entries, source="yaml")


def _entry_from_mapping(item: dict[str, Any]) -> BasketEntry:
    underlyings = item.get("underlyings") or item.get("underlying") or ()
    if isinstance(underlyings, str):
        underlyings = (underlyings,)
    return BasketEntry(
        strategy_id=str(item["strategy_id"]),
        underlyings=tuple(underlyings),
        weight=float(item.get("weight", 1.0)),
        max_lots=int(item.get("max_lots", 1)),
        stage=str(item.get("stage", "shadow")),
    )


def _basket(session: str, market: str, entries: tuple[BasketEntry, ...], *, source: str) -> Basket:
    payload = {
        "session": session,
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
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return Basket(
        session=session,
        market=market,
        entries=entries,
        source=source,
        basket_hash=digest,
    )
