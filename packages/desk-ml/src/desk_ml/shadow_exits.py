"""Per-trade alternative exits. Log only. Never places an order.

Frozen variants sit next to the default 20-minute TIME hold. Trading them is
off (``trade: false``). Shadow logging is on unless SHADOW_LOG / the yaml
``shadow_log`` flag is off.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from desk_ml.persist import repo_root
from desk_ml.shadow_log import append_shadow_row, shadow_logging_enabled, shadow_path

IST = timezone(timedelta(hours=5, minutes=30))
SCHEMA = "shadow-exit-v1"
FLAG_ENV = "SHADOW_EXIT_VARIANTS"
TRADE_ENV = "PAPER_EXIT_VARIANTS"
CONFIG_REL = Path("config") / "shadow" / "exit_variants.yaml"

R13_T10 = "R13_T10"
R21_T10 = "R21_T10"
R17_TR30 = "R17_TR30"
R23_T30 = "R23_T30"
R09_TR30 = "R09_TR30"
DEAD3_7 = "DEAD3_7"

DEFAULT_VARIANTS: tuple[dict[str, Any], ...] = (
    {"id": R13_T10, "kind": "target", "pct": 0.10},
    {"id": R21_T10, "kind": "target", "pct": 0.10},
    {"id": R17_TR30, "kind": "trail", "pct": 0.30},
    {"id": R23_T30, "kind": "target", "pct": 0.30},
    {"id": R09_TR30, "kind": "trail", "pct": 0.30},
    {"id": DEAD3_7, "kind": "dead", "pct": 0.03, "after_min": 7},
)


def _truthy(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def load_config(
    root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Yaml when present; frozen defaults otherwise. Env overrides the flags."""
    env = environ if environ is not None else os.environ
    cfg: dict[str, Any] = {
        "trade": False,
        "shadow_log": True,
        "hold_min_default": 20,
        "variants": [dict(v) for v in DEFAULT_VARIANTS],
    }
    path = (Path(root) if root is not None else repo_root()) / CONFIG_REL
    if path.is_file():
        try:
            import yaml  # type: ignore[import-untyped]

            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                if "trade" in loaded:
                    cfg["trade"] = bool(loaded["trade"])
                if "shadow_log" in loaded:
                    cfg["shadow_log"] = bool(loaded["shadow_log"])
                if loaded.get("hold_min_default") is not None:
                    cfg["hold_min_default"] = int(loaded["hold_min_default"])
                rows = loaded.get("variants")
                if isinstance(rows, list) and rows:
                    cfg["variants"] = [dict(r) for r in rows if isinstance(r, dict) and r.get("id")]
        except Exception:  # noqa: BLE001 — missing PyYAML must not stop paper
            pass
    if FLAG_ENV in env:
        cfg["shadow_log"] = _truthy(env.get(FLAG_ENV), True)
    if TRADE_ENV in env:
        cfg["trade"] = _truthy(env.get(TRADE_ENV), False)
    return cfg


def logging_enabled(
    engine: Any = None,
    *,
    root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> bool:
    cfg = load_config(root, environ)
    if not cfg["shadow_log"]:
        return False
    return shadow_logging_enabled(engine)


def trade_enabled(
    *,
    root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> bool:
    return bool(load_config(root, environ)["trade"])


def _minutes_between(start: str, end: str) -> int:
    sh, sm = (int(p) for p in start.split(":"))
    eh, em = (int(p) for p in end.split(":"))
    return (eh * 60 + em) - (sh * 60 + sm)


def simulate_one(
    path: Sequence[tuple[str, float]],
    *,
    entry: float,
    variant: Mapping[str, Any],
    hold_min: int = 20,
) -> dict[str, Any]:
    """First hit for one variant. Falls back to TIME at the last path print / hold."""
    kind = str(variant.get("kind") or "")
    pct = float(variant.get("pct") or 0.0)
    after_min = int(variant.get("after_min") or 0)
    start = path[0][0] if path else ""
    peak = float(entry)
    for hhmm, px in path:
        held = _minutes_between(start, hhmm) if start else 0
        if kind == "target" and px >= entry * (1.0 + pct):
            return {
                "id": variant["id"],
                "kind": kind,
                "hit": True,
                "reason": f"TARGET_{int(round(pct * 100))}",
                "exit_min": hhmm,
                "exit": round(float(px), 4),
                "held_min": held,
            }
        if kind == "trail":
            if px > peak:
                peak = float(px)
            if peak > entry and px <= peak * (1.0 - pct):
                return {
                    "id": variant["id"],
                    "kind": kind,
                    "hit": True,
                    "reason": f"TRAIL_{int(round(pct * 100))}",
                    "exit_min": hhmm,
                    "exit": round(float(px), 4),
                    "held_min": held,
                    "peak": round(peak, 4),
                }
        if kind == "dead" and held >= after_min and abs(px / entry - 1.0) < pct:
            return {
                "id": variant["id"],
                "kind": kind,
                "hit": True,
                "reason": "DEAD",
                "exit_min": hhmm,
                "exit": round(float(px), 4),
                "held_min": held,
            }
    last_min, last_px = path[-1] if path else ("", entry)
    held = _minutes_between(start, last_min) if start and last_min else hold_min
    return {
        "id": variant["id"],
        "kind": kind,
        "hit": False,
        "reason": "TIME",
        "exit_min": last_min,
        "exit": round(float(last_px), 4),
        "held_min": held,
    }


def simulate_all(
    path: Sequence[tuple[str, float]],
    *,
    entry: float,
    hold_min: int = 20,
    variants: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    rows = variants if variants is not None else DEFAULT_VARIANTS
    return {str(v["id"]): simulate_one(path, entry=entry, variant=v, hold_min=hold_min) for v in rows}


def build_exit_row(trade: Mapping[str, Any], variants: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ts = int(trade.get("closed_ts") or trade.get("opened_ts") or trade.get("last_updated_ts") or 0)
    return {
        "schema": SCHEMA,
        "ts": ts,
        "trade_id": trade.get("trade_id"),
        "rule_id": trade.get("rule_id"),
        "underlying": trade.get("underlying"),
        "side": trade.get("side"),
        "entry": trade.get("entry"),
        "entry_min": trade.get("entry_min"),
        "default": {
            "hold_min": 20,
            "reason": trade.get("exit_reason") or "TIME",
            "exit_min": trade.get("exit_min"),
            "exit": trade.get("exit") or trade.get("last_ltp"),
            "status": trade.get("status"),
        },
        "variants": dict(variants),
        "execution": "refused",
        "orders": "REFUSED",
        "promote": False,
        "shadow": True,
    }


def _logged_trade_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ids
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("schema") == SCHEMA and row.get("trade_id"):
            ids.add(str(row["trade_id"]))
    return ids


def log_trade_exits(
    trade: Mapping[str, Any],
    variants: Mapping[str, Mapping[str, Any]],
    *,
    root: Path,
    engine: Any = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """Append one shadow-exit-v1 row. Skips open trades and duplicates. No broker."""
    if trade.get("status") != "CLOSED":
        return None
    if not logging_enabled(engine, root=root, environ=environ):
        return None
    ctx = getattr(engine, "ctx", None) if engine is not None else None
    if ctx is not None and not getattr(ctx, "write", True):
        return None
    ts = int(trade.get("closed_ts") or trade.get("opened_ts") or 0)
    if ts <= 0:
        day = datetime.now(IST).date().isoformat()
        ts = int(datetime.fromisoformat(f"{day}T{trade.get('exit_min') or '15:30'}:00+05:30").timestamp())
    handle = engine if engine is not None else SimpleNamespace(root=root, shadow_log=True)
    path = shadow_path(handle, ts)
    if path is None:
        return None
    if str(trade.get("trade_id")) in _logged_trade_ids(path):
        return None
    row = build_exit_row(trade, variants)
    row["ts"] = ts
    append_shadow_row(handle, row)
    return row


def attach_and_log(
    trades: Sequence[Mapping[str, Any]],
    *,
    root: Path,
    engine: Any = None,
    environ: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Log closed trades that already carry ``exit_variants``. Returns rows written."""
    written: list[dict[str, Any]] = []
    for trade in trades:
        variants = trade.get("exit_variants")
        if not isinstance(variants, dict) or not variants:
            continue
        row = log_trade_exits(trade, variants, root=root, engine=engine, environ=environ)
        if row is not None:
            written.append(row)
    return written
