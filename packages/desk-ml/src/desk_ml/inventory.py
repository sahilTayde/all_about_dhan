"""Recon cache inventory. Cache JSON only. No Dhan HTTP. No Super Order."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from desk_ml.persist import repo_root
from desk_ml.tape import INDEX_SIDS, _chart_closes, _minute_key, load_index_closes, load_premium_side, load_triples

IST = timezone(timedelta(hours=5, minutes=30))


def ts_to_ist_date(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=IST).date().isoformat()


def window_bounds(*, as_of: Optional[datetime] = None, calendar_days: int = 21) -> tuple[datetime, int, int]:
    now = as_of or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    else:
        now = now.astimezone(IST)
    start = (now - timedelta(days=calendar_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return now, int(start.timestamp()), int(now.timestamp())


def _span(ts_list: list[int]) -> dict[str, Any]:
    if not ts_list:
        return {"n": 0, "first_ts": None, "last_ts": None, "first_ist": None, "last_ist": None}
    lo, hi = min(ts_list), max(ts_list)
    return {
        "n": len(ts_list),
        "first_ts": lo,
        "last_ts": hi,
        "first_ist": ts_to_ist_date(lo),
        "last_ist": ts_to_ist_date(hi),
    }


def _in_window(ts: int, min_ts: int, max_ts: int) -> bool:
    return min_ts <= ts <= max_ts


def inventory_index(root: Path, *, min_ts: int, max_ts: int) -> dict[str, Any]:
    ohlc = root / "data" / "recon" / "ohlc"
    out: dict[str, Any] = {}
    for und, sid in INDEX_SIDS.items():
        files: list[dict[str, Any]] = []
        all_ts: list[int] = []
        recent_ts: list[int] = []
        if ohlc.is_dir():
            for path in sorted(ohlc.glob(f"INDEX_IDX_I_{sid}_1_*.json")):
                try:
                    blob = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if not isinstance(blob, dict):
                    continue
                closes = _chart_closes(blob)
                file_ts = [_minute_key(ts) for ts, _ in closes]
                all_ts.extend(file_ts)
                recent = [t for t in file_ts if _in_window(t, min_ts, max_ts)]
                recent_ts.extend(recent)
                files.append({"path": path.name, **_span(file_ts), "n_in_window": len(recent)})
        out[und] = {
            "security_id": sid,
            "files": len(files),
            "all": _span(all_ts),
            "last_21d": _span(recent_ts),
            "window_missing": len(recent_ts) == 0,
        }
        # keep file list compact: only those that touch the window or the newest file
        touching = [f for f in files if f["n_in_window"] > 0]
        out[und]["window_files"] = touching[-8:]
        if files and not touching:
            out[und]["newest_file"] = files[-1]
    return out


def inventory_premium_tape(root: Path, *, min_ts: int, max_ts: int) -> dict[str, Any]:
    folder = root / "data" / "recon" / "premium_tape"
    names = ("NIFTY", "BANKNIFTY", "SENSEX")
    out: dict[str, Any] = {}
    for und in names:
        days: list[str] = []
        if folder.is_dir():
            for path in sorted(folder.glob(f"{und}_ATM_1m_*.json")):
                days.append(path.stem.replace(f"{und}_ATM_1m_", ""))
        ce = load_premium_side(und, "ce", root=root)
        pe = load_premium_side(und, "pe", root=root)
        ce_ts = list(ce)
        pe_ts = list(pe)
        ce_win = [t for t in ce_ts if _in_window(t, min_ts, max_ts)]
        pe_win = [t for t in pe_ts if _in_window(t, min_ts, max_ts)]
        out[und] = {
            "atm_day_files": days,
            "ce_all": _span(ce_ts),
            "pe_all": _span(pe_ts),
            "ce_last_21d": _span(ce_win),
            "pe_last_21d": _span(pe_win),
            "window_missing": len(ce_win) == 0 and len(pe_win) == 0,
        }
    return out


def inventory_optidx(root: Path, *, min_ts: int, max_ts: int) -> dict[str, Any]:
    ohlc = root / "data" / "recon" / "ohlc"
    files: list[dict[str, Any]] = []
    if ohlc.is_dir():
        for path in sorted(ohlc.glob("OPTIDX_NSE_FNO_*_1_*.json")):
            try:
                blob = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(blob, dict):
                continue
            ts_list = [_minute_key(ts) for ts, _ in _chart_closes(blob)]
            recent = [t for t in ts_list if _in_window(t, min_ts, max_ts)]
            span = _span(ts_list)
            files.append(
                {
                    "path": path.name,
                    **span,
                    "n_in_window": len(recent),
                    "window_first_ist": ts_to_ist_date(min(recent)) if recent else None,
                    "window_last_ist": ts_to_ist_date(max(recent)) if recent else None,
                }
            )
    in_window = [f for f in files if f["n_in_window"] > 0]
    return {
        "optidx_1m_files": len(files),
        "optidx_1m_files_touching_window": len(in_window),
        "window_missing": len(in_window) == 0,
        "note": "OPTIDX 1m is strike-sid cache (NIFTY/SENSEX CE/PE when present). Not ATM rolling tape.",
        "files_in_window": in_window[:40],
    }


def inventory_recon(
    *,
    root: Optional[Path] = None,
    calendar_days: int = 21,
    as_of: Optional[datetime] = None,
    underlyings: tuple[str, ...] = ("NIFTY", "SENSEX"),
) -> dict[str, Any]:
    base = root or repo_root()
    now, min_ts, max_ts = window_bounds(as_of=as_of, calendar_days=calendar_days)
    index = inventory_index(base, min_ts=min_ts, max_ts=max_ts)
    premium = inventory_premium_tape(base, min_ts=min_ts, max_ts=max_ts)
    optidx = inventory_optidx(base, min_ts=min_ts, max_ts=max_ts)
    joins: dict[str, Any] = {}
    for und in underlyings:
        full_triples, full_meta = load_triples(und, root=base)
        win_triples, win_meta = load_triples(und, root=base, min_ts=min_ts, max_ts=max_ts)
        idx = load_index_closes(und, root=base)
        joins[und] = {
            "old_cache_triples": full_meta,
            "last_21d_triples": win_meta,
            "index_all": _span(list(idx)),
            "week_tape_missing": win_meta.get("aligned_triples", 0) == 0,
            "honest": (
                "1–3 week aligned INDEX∩ATM CE∩ATM PE triples missing in recon cache"
                if not win_triples
                else f"{len(win_triples)} aligned triples in last {calendar_days} calendar days"
            ),
            "full_span_ist": {
                "first": ts_to_ist_date(full_triples[0].ts) if full_triples else None,
                "last": ts_to_ist_date(full_triples[-1].ts) if full_triples else None,
                "n": len(full_triples),
            },
        }
    gaps = []
    for und, row in joins.items():
        if row["week_tape_missing"]:
            gaps.append(f"DATA_INSUFFICIENT: {und} last-{calendar_days}d INDEX+ATM tape join empty")
        if row["old_cache_triples"].get("aligned_triples", 0) == 0:
            gaps.append(f"DATA_INSUFFICIENT: {und} no aligned triples on old cache either")
    if optidx["window_missing"]:
        gaps.append(f"DATA_INSUFFICIENT: no OPTIDX 1m bars in last {calendar_days} calendar days")
    return {
        "ok": True,
        "live_dhan": False,
        "as_of_ist": now.isoformat(timespec="seconds"),
        "calendar_days": calendar_days,
        "window_start_ist": datetime.fromtimestamp(min_ts, tz=IST).isoformat(timespec="seconds"),
        "index_1m": index,
        "premium_tape": premium,
        "optidx_1m": optidx,
        "joins": joins,
        "data_gaps": gaps,
        "promote": False,
        "production_params_written": False,
        "verdict": "NO_PROMOTE",
        "execution": "refused",
    }
