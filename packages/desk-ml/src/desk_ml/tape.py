"""Load INDEX 1m + ATM CE/PE 1m from recon cache + warehouse. No Dhan HTTP. No poll loop."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from desk_ml.features import Triple
from desk_ml.persist import repo_root

INDEX_SIDS = {"NIFTY": "13", "BANKNIFTY": "25", "SENSEX": "51"}
IST = timezone(timedelta(hours=5, minutes=30))
WAREHOUSE_ATM = {"ce": "{und}_ATM_CE", "pe": "{und}_ATM_PE"}
EMBARGO_BARS_DEFAULT = 5


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


def ist_calendar_date(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=IST).date().isoformat()


def parse_ts(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        if val > 1e12:
            val = val / 1000.0
        return int(val)
    text = str(raw).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return int(dt.timestamp())


def warehouse_path(root: Path) -> Path:
    return root / "data" / "knowledge" / "warehouse.sqlite"


def _merge_close(merged: dict[int, float], ts_raw: Any, close_raw: Any) -> None:
    ts_i = parse_ts(ts_raw)
    if ts_i is None:
        return
    try:
        close = float(close_raw)
    except (TypeError, ValueError):
        return
    merged[_minute_key(ts_i)] = close


def _warehouse_closes(db: Path, *, symbol: str, use_ohlc_tf: bool) -> dict[int, float]:
    merged: dict[int, float] = {}
    if not db.is_file():
        return merged
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        queries: list[tuple[str, tuple[Any, ...]]] = []
        if use_ohlc_tf:
            queries.append(
                (
                    "SELECT ts, close FROM ohlc_bars WHERE symbol=? AND timeframe=? AND close IS NOT NULL",
                    (symbol, "1m"),
                )
            )
        queries.append(("SELECT ts, close FROM bars_1m WHERE symbol=? AND close IS NOT NULL", (symbol,)))
        for sql, args in queries:
            try:
                rows = conn.execute(sql, args).fetchall()
            except sqlite3.Error:
                continue
            for row in rows:
                _merge_close(merged, row["ts"], row["close"])
        conn.close()
    except sqlite3.Error:
        return merged
    return merged


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
    merged.update(_warehouse_closes(warehouse_path(base), symbol=underlying.upper(), use_ohlc_tf=True))
    return merged


def load_premium_side(underlying: str, side: str, *, root: Optional[Path] = None) -> dict[int, float]:
    base = root or repo_root()
    folder = base / "data" / "recon" / "premium_tape"
    merged: dict[int, float] = {}
    if folder.is_dir():
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
    symbol = WAREHOUSE_ATM[side.lower()].format(und=underlying.upper())
    merged.update(_warehouse_closes(warehouse_path(base), symbol=symbol, use_ohlc_tf=True))
    return merged


def load_premium_ohlcv(underlying: str, side: str, *, root: Optional[Path] = None) -> dict[int, tuple[float, float]]:
    """ts -> (close, volume). Volume 0 is allowed (VWMA falls back to SMA)."""
    base = root or repo_root()
    folder = base / "data" / "recon" / "premium_tape"
    merged: dict[int, tuple[float, float]] = {}
    if folder.is_dir():
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
                try:
                    vol = float(row.get("volume") or 0.0)
                except (TypeError, ValueError):
                    vol = 0.0
                merged[ts] = (close, vol)
    for ts, close in load_premium_side(underlying, side, root=base).items():
        merged.setdefault(ts, (close, 0.0))
    return merged


def filter_ts_map(series: dict[int, Any], *, min_ts: Optional[int] = None, max_ts: Optional[int] = None) -> dict[int, Any]:
    if min_ts is None and max_ts is None:
        return series
    out: dict[int, Any] = {}
    for ts, val in series.items():
        if min_ts is not None and ts < min_ts:
            continue
        if max_ts is not None and ts > max_ts:
            continue
        out[ts] = val
    return out


def load_triples(
    underlying: str,
    *,
    root: Optional[Path] = None,
    min_ts: Optional[int] = None,
    max_ts: Optional[int] = None,
) -> tuple[list[Triple], dict[str, Any]]:
    base = root or repo_root()
    idx = filter_ts_map(load_index_closes(underlying, root=base), min_ts=min_ts, max_ts=max_ts)
    ce = filter_ts_map(load_premium_side(underlying, "ce", root=base), min_ts=min_ts, max_ts=max_ts)
    pe = filter_ts_map(load_premium_side(underlying, "pe", root=base), min_ts=min_ts, max_ts=max_ts)
    keys = sorted(set(idx) & set(ce) & set(pe))
    triples = [Triple(ts=k, idx_close=idx[k], ce_close=ce[k], pe_close=pe[k]) for k in keys]
    meta: dict[str, Any] = {
        "underlying": underlying.upper(),
        "index_bars": len(idx),
        "ce_bars": len(ce),
        "pe_bars": len(pe),
        "aligned_triples": len(triples),
        "source": "recon_ohlc+premium_tape+warehouse(ohlc_bars|bars_1m)+warehouse_ATM_if_present",
        "warehouse_sqlite": warehouse_path(base).is_file(),
        "live_dhan": False,
        "min_ts": min_ts,
        "max_ts": max_ts,
    }
    if triples:
        meta["first_ts"] = triples[0].ts
        meta["last_ts"] = triples[-1].ts
    if not triples:
        meta["data_gaps"] = ["DATA_INSUFFICIENT: no aligned 1m INDEX+CE+PE triples in recon cache"]
    return triples, meta


def thin_hold(*, underlying: str, reason: str, tape: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Fewer than two INDEX+CE+PE prints: HOLD new paper CE/PE. Not a promote."""
    return {
        "ok": True,
        "status": "DATA_INSUFFICIENT",
        "underlying": underlying.upper(),
        "reason": reason,
        "follow_gap": False,
        "session_action": "HOLD",
        "allow_new_paper_ce_pe": False,
        "promote": False,
        "production_params_written": False,
        "execution": "refused",
        "oos_claim": False,
        "win_rate": None,
        "tape": tape or {},
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
    }


def dual_tape_dir(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / "data" / "recon" / "paper_watch" / "DUAL-TAPE"


def _snap_ltps(snap: dict[str, Any]) -> Optional[tuple[float, float, float]]:
    try:
        idx = float(snap["index_ltp"])
        ce = float(snap["atm_ce_ltp"])
        pe = float(snap["atm_pe_ltp"])
    except (KeyError, TypeError, ValueError):
        return None
    return idx, ce, pe


def _opt_float(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def merge_wing_quotes(prev: Any, new: Any) -> dict[str, Any]:
    """Keep last LTP per strike and the running minute low. Never drop a booked strike's low."""
    out: dict[str, Any] = {}
    if isinstance(prev, dict):
        for key, cell in prev.items():
            if isinstance(cell, dict):
                out[str(key)] = dict(cell)
    if not isinstance(new, dict):
        return out
    for key, cell in new.items():
        if not isinstance(cell, dict):
            continue
        sk = str(key)
        old = out.get(sk) if isinstance(out.get(sk), dict) else {}
        merged = dict(cell)
        for side in ("ce", "pe"):
            ltp = _opt_float(cell.get(side))
            if ltp is None:
                ltp = _opt_float(old.get(side))
            prev_low = _opt_float(old.get(f"{side}_low")) or _opt_float(old.get(side))
            cell_low = _opt_float(cell.get(f"{side}_low")) or _opt_float(cell.get(side))
            lows = [x for x in (prev_low, cell_low, ltp) if x is not None]
            if ltp is not None:
                merged[side] = ltp
            if lows:
                merged[f"{side}_low"] = min(lows)
        out[sk] = merged
    return out


def _snap_row(snap: dict[str, Any], as_of: Optional[int]) -> Optional[dict[str, Any]]:
    ltps = _snap_ltps(snap)
    if ltps is None:
        return None
    ts = parse_ts(snap.get("as_of_ist")) or as_of
    if ts is None:
        return None
    return {
        "ts": _minute_key(ts),
        "idx": ltps[0],
        "ce": ltps[1],
        "pe": ltps[2],
        "atm_strike": _opt_float(snap.get("atm_strike")),
        "itm_ce": _opt_float(snap.get("itm_ce_ltp")),
        "itm_pe": _opt_float(snap.get("itm_pe_ltp")),
        "itm_ce_strike": _opt_float(snap.get("itm_ce_strike")),
        "itm_pe_strike": _opt_float(snap.get("itm_pe_strike")),
        "wing_quotes": snap.get("wing_quotes") if isinstance(snap.get("wing_quotes"), dict) else {},
        "idx_volume": _opt_float(snap.get("index_volume")),
    }


def load_dual_tape_triples(
    underlying: str,
    *,
    root: Optional[Path] = None,
    session_ist_date: Optional[str] = None,
) -> tuple[list[Triple], dict[str, Any]]:
    """Consecutive dual-tape ticks with INDEX + ATM CE + ATM PE LTP. Paper gather only."""
    base = root or repo_root()
    folder = dual_tape_dir(base)
    und = underlying.upper()
    ticks: list[dict[str, Any]] = []
    files: list[Path] = []
    if folder.is_dir():
        files = sorted(folder.glob("*.jsonl"))
        latest = folder / "latest.json"
        if latest.is_file():
            files.append(latest)
    seen: set[tuple[int, float, float, float]] = set()
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        blobs: list[Any]
        if path.suffix == ".jsonl":
            blobs = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    blobs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        else:
            try:
                blobs = [json.loads(text)]
            except json.JSONDecodeError:
                continue
        for blob in blobs:
            if not isinstance(blob, dict):
                continue
            as_of = parse_ts(blob.get("as_of_ist"))
            for snap in blob.get("underlyings") or []:
                if not isinstance(snap, dict):
                    continue
                if str(snap.get("underlying") or "").upper() != und:
                    continue
                row = _snap_row(snap, as_of)
                if row is None:
                    continue
                key = (row["ts"], row["idx"], row["ce"], row["pe"])
                if key in seen:
                    continue
                seen.add(key)
                ticks.append(row)
    by_min: dict[int, dict[str, Any]] = {}
    for row in ticks:
        ts = int(row["ts"])
        prev = by_min.get(ts)
        if prev is None:
            by_min[ts] = {
                **row,
                "ce_low": row["ce"],
                "pe_low": row["pe"],
                "itm_ce_low": row.get("itm_ce"),
                "itm_pe_low": row.get("itm_pe"),
                "wing_quotes": merge_wing_quotes({}, row.get("wing_quotes")),
            }
            continue
        prev["idx"] = row["idx"]
        prev["ce"] = row["ce"]
        prev["pe"] = row["pe"]
        prev["ce_low"] = min(float(prev["ce_low"]), float(row["ce"]))
        prev["pe_low"] = min(float(prev["pe_low"]), float(row["pe"]))
        if row.get("atm_strike") is not None:
            prev["atm_strike"] = row["atm_strike"]
        if row.get("itm_ce") is not None:
            prev["itm_ce"] = row["itm_ce"]
            prev["itm_ce_low"] = (
                min(float(prev["itm_ce_low"]), float(row["itm_ce"]))
                if prev.get("itm_ce_low") is not None
                else row["itm_ce"]
            )
        if row.get("itm_pe") is not None:
            prev["itm_pe"] = row["itm_pe"]
            prev["itm_pe_low"] = (
                min(float(prev["itm_pe_low"]), float(row["itm_pe"]))
                if prev.get("itm_pe_low") is not None
                else row["itm_pe"]
            )
        if row.get("itm_ce_strike") is not None:
            prev["itm_ce_strike"] = row["itm_ce_strike"]
        if row.get("itm_pe_strike") is not None:
            prev["itm_pe_strike"] = row["itm_pe_strike"]
        if row.get("idx_volume") is not None:
            prev["idx_volume"] = row["idx_volume"]
        prev["wing_quotes"] = merge_wing_quotes(prev.get("wing_quotes"), row.get("wing_quotes"))
    ordered = [by_min[k] for k in sorted(by_min)]
    triples = [
        Triple(
            ts=int(row["ts"]),
            idx_close=float(row["idx"]),
            ce_close=float(row["ce"]),
            pe_close=float(row["pe"]),
            atm_strike=row.get("atm_strike"),
            ce_low=float(row["ce_low"]),
            pe_low=float(row["pe_low"]),
            itm_ce_close=row.get("itm_ce"),
            itm_pe_close=row.get("itm_pe"),
            itm_ce_strike=row.get("itm_ce_strike"),
            itm_pe_strike=row.get("itm_pe_strike"),
            itm_ce_low=row.get("itm_ce_low"),
            itm_pe_low=row.get("itm_pe_low"),
            wing_quotes=row.get("wing_quotes") or None,
            idx_volume=row.get("idx_volume"),
        )
        for row in ordered
    ]
    if session_ist_date:
        triples = [t for t in triples if ist_calendar_date(int(t.ts)) == session_ist_date]
    meta: dict[str, Any] = {
        "underlying": und,
        "source": "dual_tape_jsonl",
        "aligned_triples": len(triples),
        "session_ist_date": session_ist_date,
        "live_dhan": False,
        "execution": "refused",
    }
    if triples:
        meta["first_ts"] = triples[0].ts
        meta["last_ts"] = triples[-1].ts
    else:
        meta["data_gaps"] = [
            "DATA_INSUFFICIENT: dual-tape JSONL has no INDEX+ATM CE+PE LTP ticks for this underlying"
        ]
    return triples, meta


def embargo_train_rows(rows: list[dict], *, embargo_bars: int = EMBARGO_BARS_DEFAULT) -> tuple[list[dict], dict[str, Any]]:
    """AFML analog: drop overlapping last labels from the fit set. Not CPCV. Not OOS."""
    n = max(0, int(embargo_bars))
    if n <= 0 or len(rows) < 16 + n:
        return rows, {
            "embargo_bars": 0,
            "applied": False,
            "reason": "DATA_INSUFFICIENT_FOR_EMBARGO" if n and len(rows) < 16 + n else "none",
            "n_train": len(rows),
            "n_held": 0,
            "cpcv": False,
            "oos_claim": False,
        }
    train = rows[:-n]
    return train, {
        "embargo_bars": n,
        "applied": True,
        "reason": "purge last labels from fit (AFML excerpt analog; not CPCV)",
        "n_train": len(train),
        "n_held": n,
        "cpcv": False,
        "oos_claim": False,
    }


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
