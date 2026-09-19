"""Paper lot size + desk capital. Lot from Dhan instrument master when available. No live orders."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from desk_ml.persist import repo_root

STARTING_CAPITAL_INR = 10000.0
INDEX_UNDERLYING_SID = {"NIFTY": "13", "BANKNIFTY": "25", "SENSEX": "51"}
CACHE_NAME = "optidx_lot_cache.json"

_LOT_MEM: dict[str, tuple[Optional[int], str]] = {}


def cache_path(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / "data" / "recon" / CACHE_NAME


def _from_disk(root: Path, und: str) -> Optional[tuple[int, str]]:
    path = cache_path(root)
    if not path.is_file():
        return None
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    row = (blob or {}).get(und.upper())
    if not isinstance(row, dict):
        return None
    try:
        lot = int(row["lot_size"])
    except (KeyError, TypeError, ValueError):
        return None
    if lot <= 0:
        return None
    return lot, str(row.get("source") or "disk_cache")


def _write_disk(root: Path, und: str, lot: int, source: str) -> None:
    path = cache_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob: dict[str, Any] = {}
    if path.is_file():
        try:
            blob = json.loads(path.read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError):
            blob = {}
    blob[und.upper()] = {"lot_size": lot, "source": source}
    path.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")


def _parse_master_lots(text: str) -> dict[str, int]:
    """Mode LOT_SIZE per INDEX underlying from detailed OPTIDX rows. No invented IDs."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {}
    upper = {name.upper(): name for name in reader.fieldnames}
    lot_col = upper.get("LOT_SIZE") or upper.get("SEM_LOT_UNITS")
    und_id_col = upper.get("UNDERLYING_SECURITY_ID")
    inst_col = upper.get("INSTRUMENT") or upper.get("SEM_INSTRUMENT_NAME")
    und_sym_col = upper.get("UNDERLYING_SYMBOL") or upper.get("SM_SYMBOL_NAME")
    if lot_col is None:
        return {}
    buckets: dict[str, list[int]] = {k: [] for k in INDEX_UNDERLYING_SID}
    sid_to_name = {v: k for k, v in INDEX_UNDERLYING_SID.items()}
    for row in reader:
        inst = str(row.get(inst_col) or "").upper() if inst_col else ""
        if inst and inst not in {"OPTIDX", "OPTIDX "}:
            continue
        name = None
        if und_id_col:
            sid = str(row.get(und_id_col) or "").strip()
            name = sid_to_name.get(sid)
        if name is None and und_sym_col:
            sym = str(row.get(und_sym_col) or "").upper().replace(" ", "")
            if "BANKNIFTY" in sym:
                name = "BANKNIFTY"
            elif "SENSEX" in sym:
                name = "SENSEX"
            elif sym == "NIFTY" or sym.startswith("NIFTY"):
                if "BANK" in sym or "FIN" in sym:
                    continue
                name = "NIFTY"
        if name is None:
            continue
        try:
            lot = int(float(row.get(lot_col)))
        except (TypeError, ValueError):
            continue
        if lot > 0:
            buckets[name].append(lot)
    out: dict[str, int] = {}
    for und, vals in buckets.items():
        if not vals:
            continue
        out[und] = Counter(vals).most_common(1)[0][0]
    return out


def resolve_lot_size(underlying: str, *, root: Optional[Path] = None) -> tuple[Optional[int], str]:
    u = underlying.upper()
    if u in _LOT_MEM:
        return _LOT_MEM[u]
    base = root or repo_root()
    disk = _from_disk(base, u)
    if disk is not None:
        _LOT_MEM[u] = disk
        return disk
    try:
        from dhan_client import DhanClient

        client = DhanClient(dry_run=False)
        text = client.instruments.fetch_scrip_master_text(detailed=True)
        client.close()
    except Exception as exc:  # noqa: BLE001
        _LOT_MEM[u] = (None, f"DATA_INSUFFICIENT: instrument_master {type(exc).__name__}")
        return _LOT_MEM[u]
    parsed = _parse_master_lots(text)
    if u not in parsed:
        _LOT_MEM[u] = (None, "DATA_INSUFFICIENT: no OPTIDX lot in instrument master")
        return _LOT_MEM[u]
    lot = parsed[u]
    _write_disk(base, u, lot, "instrument_master_detailed")
    for name, val in parsed.items():
        _write_disk(base, name, val, "instrument_master_detailed")
        _LOT_MEM[name] = (val, "instrument_master_detailed")
    return _LOT_MEM[u]


def size_lots(
    *,
    entry: float,
    lot_size: Optional[int],
    capital_inr: float,
    min_lots: int = 1,
) -> dict[str, Any]:
    want = max(1, int(min_lots or 1))
    if lot_size is None or lot_size <= 0 or entry <= 0:
        return {
            "lots": want,
            "lot_size": lot_size,
            "qty": None,
            "notional_inr": None,
            "capital_inr": capital_inr,
            "lot_status": "DATA_INSUFFICIENT",
        }
    one = float(entry) * int(lot_size)
    if one > float(capital_inr):
        return {
            "lots": 1,
            "lot_size": int(lot_size),
            "qty": int(lot_size),
            "notional_inr": round(one, 2),
            "capital_inr": capital_inr,
            "lot_status": "ONE_LOT_EXCEEDS_PAPER_CAPITAL_STILL",
        }
    afford = max(1, int(float(capital_inr) // one))
    lots = min(want, afford)
    status = "OK" if lots >= want else "CLIPPED_TO_CAPITAL"
    qty = lots * int(lot_size)
    return {
        "lots": lots,
        "lot_size": int(lot_size),
        "qty": qty,
        "notional_inr": round(float(entry) * qty, 2),
        "capital_inr": capital_inr,
        "lot_status": status,
    }


def pnl_inr(*, points: float, lot_size: Optional[int], lots: int) -> Optional[float]:
    if lot_size is None or lot_size <= 0:
        return None
    return round(float(points) * int(lot_size) * int(lots), 2)
