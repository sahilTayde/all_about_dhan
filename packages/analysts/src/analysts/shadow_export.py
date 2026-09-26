"""One CSV row per session, minute and underlying from shadow ANALYST_VOTE audit rows."""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Union

IST = timezone(timedelta(hours=5, minutes=30))

# Stable column order. Extra shadow ids discovered in the log are appended.
CORE_IDS = (
    "rng60_atr",
    "rng5_3m",
    "rv30",
    "er30",
    "br3_3m",
    "chasing",
    "high_vol",
    "minutes_since_prior_trade",
    "day_direction",
    "late_day_momentum",
    "expiry_day",
    "gex",
)


def _minute(payload: dict[str, Any], event_ts: str) -> tuple[str, str]:
    raw = payload.get("ts")
    if raw is not None:
        try:
            dt = datetime.fromtimestamp(int(raw), IST)
            return dt.date().isoformat(), dt.strftime("%H:%M")
        except (TypeError, ValueError, OSError):
            pass
    try:
        dt = datetime.fromisoformat(str(event_ts))
    except ValueError:
        return "", ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    dt = dt.astimezone(IST)
    return dt.date().isoformat(), dt.strftime("%H:%M")


def _is_shadow(payload: dict[str, Any]) -> bool:
    meta = payload.get("metadata") or {}
    return bool(meta.get("shadow") or payload.get("shadow"))


def rows_from_audit(path: Union[str, Path]) -> list[dict[str, Any]]:
    """Last shadow vote in each (session, minute, underlying) wins."""
    conn = sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "SELECT seq, ts, payload_json FROM events WHERE event_type = ? ORDER BY seq",
            ("ANALYST_VOTE",),
        )
        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
        ids: list[str] = list(CORE_IDS)
        seen = set(ids)
        for seq, event_ts, raw in cur:
            payload = json.loads(raw)
            if not _is_shadow(payload):
                continue
            meta = payload.get("metadata") or {}
            aid = str(payload.get("analyst_id") or "")
            if not aid:
                continue
            if aid not in seen:
                seen.add(aid)
                ids.append(aid)
            session, minute = _minute(payload, str(event_ts))
            und = str(payload.get("underlying") or "")
            key = (session, minute, und)
            row = grouped.get(key)
            if row is None:
                row = {"session": session, "minute_ist": minute, "underlying": und, "_seq": seq}
                grouped[key] = row
            if int(seq) < int(row.get("_seq") or 0):
                continue
            row["_seq"] = seq
            value = payload.get("value", meta.get("value"))
            flag = payload.get("flag", meta.get("flag"))
            row[aid] = "" if value is None else value
            row[f"{aid}_flag"] = "" if flag is None else flag
            if "expected_abs_move_pts" in meta:
                row["rng60_atr_expected_abs_move_pts"] = "" if meta["expected_abs_move_pts"] is None else meta["expected_abs_move_pts"]
            if "zero_gamma" in meta:
                row["gex_zero_gamma"] = "" if meta["zero_gamma"] is None else meta["zero_gamma"]
    finally:
        conn.close()
    ordered = sorted(grouped.values(), key=lambda r: (r["session"], r["underlying"], r["minute_ist"], r["_seq"]))
    for row in ordered:
        row.pop("_seq", None)
        row["_ids"] = ids
    return ordered


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Export shadow ANALYST_VOTE rows to one CSV row per session, minute and underlying.")
    ap.add_argument("--audit", type=Path, required=True, help="SQLite event audit log (events table)")
    ap.add_argument("--out", type=Path, required=True, help="CSV path to write")
    args = ap.parse_args(argv)
    n = export_shadow_csv(args.audit, args.out)
    print(f"wrote {n} rows to {args.out}")
    return 0


def export_shadow_csv(audit_path: Union[str, Path], out_path: Union[str, Path]) -> int:
    """Write the CSV. Returns the number of data rows."""
    data = rows_from_audit(audit_path)
    ids = list(data[0].get("_ids") or CORE_IDS) if data else list(CORE_IDS)
    for row in data:
        row.pop("_ids", None)
    fields = ["session", "minute_ist", "underlying"]
    for aid in ids:
        fields.append(aid)
        fields.append(f"{aid}_flag")
    fields.extend(["rng60_atr_expected_abs_move_pts", "gex_zero_gamma"])
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    return len(data)
