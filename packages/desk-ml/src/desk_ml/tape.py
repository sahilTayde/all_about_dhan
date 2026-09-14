"""Load INDEX 1m + ATM CE/PE 1m from recon cache. No Dhan HTTP. No poll loop."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from desk_ml.features import Triple
from desk_ml.persist import repo_root

INDEX_SIDS = {"NIFTY": "13", "BANKNIFTY": "25", "SENSEX": "51"}


def _chart_closes(payload: dict[str, Any]) -> list[tuple[int, float]]:
    data = payload
    inner = payload.get("data")
    if isinstance(inner, dict) and ("close" in inner or "timestamp" in inner):
        data = inner
    ts = data.get("timestamp") or data.get("time") or []
    closes = data.get("close") or data.get("Close") or []
    n = min(len(ts), len(closes))
    out: list[tuple[int, float]] = []
    for i in range(n):
        if ts[i] is None or closes[i] is None:
            continue
        try:
            out.append((int(ts[i]), float(closes[i])))
        except (TypeError, ValueError):
            continue
    return out


def _minute_key(ts: int) -> int:
    return int(ts) - (int(ts) % 60)


def load_index_closes(underlying: str, *, root: Optional[Path] = None) -> dict[int, float]:
    base = root or repo_root()
    sid = INDEX_SIDS.get(underlying.upper())
    merged: dict[int, float] = {}
    ohlc = base / "data" / "recon" / "ohlc"
    if sid and ohlc.is_dir():
        prefix = f"INDEX_IDX_I_{sid}_1_"
        for path in sorted(ohlc.glob(f"{prefix}*.json")):
            try:
                blob = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(blob, dict):
                continue
            for ts, close in _chart_closes(blob):
                merged[_minute_key(ts)] = close
    db = base / "data" / "knowledge" / "warehouse.sqlite"
    if db.is_file():
        try:
            conn = sqlite3.connect(str(db))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT ts, close FROM ohlc_bars WHERE symbol=? AND timeframe=? AND close IS NOT NULL",
                (underlying.upper(), "1m"),
            ).fetchall()
            conn.close()
        except sqlite3.Error:
            rows = []
        for row in rows:
            try:
                ts_raw = row["ts"]
                close = float(row["close"])
            except (TypeError, ValueError, KeyError):
                continue
            ts_i: Optional[int] = None
            if isinstance(ts_raw, (int, float)):
                ts_i = int(ts_raw)
            else:
                try:
                    ts_i = int(datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00")).timestamp())
                except ValueError:
                    continue
            merged[_minute_key(ts_i)] = close
    return merged


def load_premium_side(underlying: str, side: str, *, root: Optional[Path] = None) -> dict[int, float]:
    folder = (root or repo_root()) / "data" / "recon" / "premium_tape"
    merged: dict[int, float] = {}
    if not folder.is_dir():
        return merged
    for path in sorted(folder.glob(f"{underlying.upper()}_ATM_1m_*.json")):
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for row in blob.get(side) or []:
            try:
                ts = _minute_key(int(row["ts"]))
                close = float(row["close"])
            except (KeyError, TypeError, ValueError):
                continue
            merged[ts] = close
    return merged


def load_triples(underlying: str, *, root: Optional[Path] = None) -> tuple[list[Triple], dict[str, Any]]:
    base = root or repo_root()
    idx = load_index_closes(underlying, root=base)
    ce = load_premium_side(underlying, "ce", root=base)
    pe = load_premium_side(underlying, "pe", root=base)
    keys = sorted(set(idx) & set(ce) & set(pe))
    triples = [Triple(ts=k, idx_close=idx[k], ce_close=ce[k], pe_close=pe[k]) for k in keys]
    meta = {
        "underlying": underlying.upper(),
        "index_bars": len(idx),
        "ce_bars": len(ce),
        "pe_bars": len(pe),
        "aligned_triples": len(triples),
        "source": "recon_ohlc+premium_tape(+warehouse if present)",
        "live_dhan": False,
    }
    if not triples:
        meta["data_gaps"] = ["DATA_INSUFFICIENT: no aligned 1m INDEX+CE+PE triples in recon cache"]
    return triples, meta


def labels_from_paper_ledger(root: Optional[Path] = None, *, min_rows: int = 50) -> dict[str, Any]:
    folder = (root or repo_root()) / "data" / "recon" / "paper_ledger"
    n_took = 0
    n_hold = 0
    n_lines = 0
    if folder.is_dir():
        for path in folder.glob("*.jsonl"):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                n_lines += 1
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                action = str(obj.get("action") or obj.get("customer_action") or "").upper()
                lean = str(obj.get("lean") or obj.get("side") or obj.get("final_lean") or "").upper()
                if action == "TOOK" or lean in {"BUY_CE", "BUY_PE", "CE", "PE"}:
                    n_took += 1
                if lean == "HOLD" or action == "SKIPPED":
                    n_hold += 1
    labeled = min(n_took, n_hold)
    if labeled < min_rows:
        return {
            "status": "DATA_INSUFFICIENT",
            "reason": (
                "supervised HOLD-vs-take skipped: paper ledger lacks paired labels "
                f"(took_like={n_took}, hold_like={n_hold}, jsonl_lines={n_lines}, need>={min_rows})"
            ),
            "took_like": n_took,
            "hold_like": n_hold,
            "jsonl_lines": n_lines,
            "model": None,
        }
    return {
        "status": "SKIPPED_THIS_TICKET",
        "reason": "labels exist but ML-001 ships unsupervised only; logistic is TOKEN_ML ML-1 later, shadow, NO_PROMOTE",
        "took_like": n_took,
        "hold_like": n_hold,
        "jsonl_lines": n_lines,
        "model": None,
    }
