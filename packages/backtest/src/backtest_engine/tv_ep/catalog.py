"""Load Editor Picks catalog JSON. No Pine. Catalog agent fills entries."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from dhan_client.config import repo_root

CATALOG_REL = Path("refernece_tradingview") / "editors_picks" / "catalog.json"
MIX_RE = re.compile(r"^MIX-TV-EP-\d{3,}$")
EP_RE = re.compile(r"^EP-\d{3,}$")
ADAPTER_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")


@dataclass(frozen=True)
class ParamSpec:
    type: str
    default: float
    grid: tuple[float, ...]

    def values(self) -> tuple[float, ...]:
        return self.grid if self.grid else (self.default,)


@dataclass(frozen=True)
class CatalogEntry:
    ep_id: str
    mix_id: str
    adapter: str
    title: str = ""
    author: str = ""
    tv_url: str = ""
    origin: str = "TV-EP-STUB"
    notes: str = ""
    input_schema: dict[str, ParamSpec] = field(default_factory=dict)

    def as_meta(self) -> dict[str, Any]:
        return {
            "ep_id": self.ep_id,
            "mix_id": self.mix_id,
            "adapter": self.adapter,
            "title": self.title,
            "origin": self.origin,
            "pine_copied": False,
            "promotion": "NO_PROMOTE",
            "customer_default": False,
        }


def mix_id_ok(mix_id: str) -> bool:
    return bool(MIX_RE.match(mix_id))


def _param(raw: dict[str, Any]) -> ParamSpec:
    default = raw.get("default", 0)
    try:
        default_f = float(default)
    except (TypeError, ValueError):
        default_f = 0.0
    grid_raw = raw.get("grid") or [default_f]
    grid: list[float] = []
    for x in grid_raw:
        try:
            grid.append(float(x))
        except (TypeError, ValueError):
            continue
    return ParamSpec(
        type=str(raw.get("type") or "int"),
        default=default_f,
        grid=tuple(grid) if grid else (default_f,),
    )


def _entry(raw: dict[str, Any]) -> CatalogEntry:
    ep_id = str(raw["ep_id"])
    mix_id = str(raw["mix_id"])
    adapter = str(raw.get("adapter") or "stub")
    if not EP_RE.match(ep_id):
        raise ValueError(f"bad ep_id {ep_id}")
    if not mix_id_ok(mix_id):
        raise ValueError(f"bad mix_id {mix_id} — use MIX-TV-EP-NNN not STRAT-015+")
    if not ADAPTER_ID_RE.match(adapter):
        adapter = "stub"
    schema_raw = raw.get("input_schema") or {}
    schema: dict[str, ParamSpec] = {}
    if isinstance(schema_raw, dict):
        for k, v in schema_raw.items():
            if isinstance(v, dict) and "default" in v:
                schema[str(k)] = _param(v)
    return CatalogEntry(
        ep_id=ep_id,
        mix_id=mix_id,
        adapter=adapter,
        title=str(raw.get("title") or ""),
        author=str(raw.get("author") or ""),
        tv_url=str(raw.get("tv_url") or ""),
        origin=str(raw.get("origin") or "TV-EP-STUB"),
        notes=str(raw.get("notes") or ""),
        input_schema=schema,
    )


def _builtin_seed() -> list[CatalogEntry]:
    """Used when catalog.json is missing/empty so the factory still emits rows."""
    return [
        CatalogEntry(
            ep_id="EP-024",
            mix_id="MIX-TV-EP-024",
            adapter="sma_cross",
            title="Public SMA crossover (factory calibrator; not a listing card)",
            origin="TV-PUBLIC-RULE",
            input_schema={
                "fast": ParamSpec("int", 10, (10,)),
                "slow": ParamSpec("int", 50, (50,)),
            },
        ),
        CatalogEntry(
            ep_id="EP-025",
            mix_id="MIX-TV-EP-025",
            adapter="macd_hist",
            title="Public MACD histogram zero-cross (factory calibrator; not a listing card)",
            origin="TV-PUBLIC-RULE",
            input_schema={
                "fast": ParamSpec("int", 12, (12,)),
                "slow": ParamSpec("int", 26, (26,)),
                "signal": ParamSpec("int", 9, (9,)),
            },
        ),
        CatalogEntry(
            ep_id="EP-026",
            mix_id="MIX-TV-EP-026",
            adapter="stub",
            title="Unported Editor Pick placeholder (used only if catalog.json empty)",
            origin="TV-EP-STUB",
        ),
    ]


def catalog_path(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / CATALOG_REL


def load_catalog(path: Optional[Path] = None) -> list[CatalogEntry]:
    loc = path or catalog_path()
    if not loc.is_file():
        return list(_builtin_seed())
    raw = json.loads(loc.read_text(encoding="utf-8"))
    entries = [_entry(e) for e in (raw.get("entries") or [])]
    return entries if entries else list(_builtin_seed())
