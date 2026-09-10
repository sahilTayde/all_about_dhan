"""Index member *names* for quote resolve. Weights are NOT official.

VERIFY FROM NSE/BSE factsheet. Reconstitutions happen. Do not treat as SOURCE_FACT weights.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Optional

# Names only. weight_pct stays NULL in the warehouse.
# Lists are HYPOTHESIS / VERIFY — 03 does not certify this as the live basket.

NIFTY_50 = (
    "ADANIENT",
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "AXISBANK",
    "BAJAJ-AUTO",
    "BAJFINANCE",
    "BAJAJFINSV",
    "BEL",
    "BHARTIARTL",
    "BPCL",
    "BRITANNIA",
    "CIPLA",
    "COALINDIA",
    "DRREDDY",
    "EICHERMOT",
    "GRASIM",
    "HCLTECH",
    "HDFCBANK",
    "HDFCLIFE",
    "HEROMOTOCO",
    "HINDALCO",
    "HINDUNILVR",
    "ICICIBANK",
    "INDUSINDBK",
    "INFY",
    "ITC",
    "JSWSTEEL",
    "KOTAKBANK",
    "LT",
    "M&M",
    "MARUTI",
    "NESTLEIND",
    "NTPC",
    "ONGC",
    "POWERGRID",
    "RELIANCE",
    "SBILIFE",
    "SBIN",
    "SHRIRAMFIN",
    "SUNPHARMA",
    "TCS",
    "TATACONSUM",
    "TATAMOTORS",
    "TATASTEEL",
    "TECHM",
    "TITAN",
    "TRENT",
    "ULTRACEMCO",
    "WIPRO",
)

BANKNIFTY = (
    "AUBANK",
    "AXISBANK",
    "BANDHANBNK",
    "BANKBARODA",
    "FEDERALBNK",
    "HDFCBANK",
    "ICICIBANK",
    "IDFCFIRSTB",
    "INDUSINDBK",
    "KOTAKBANK",
    "PNB",
    "SBIN",
)

SENSEX = (
    "ASIANPAINT",
    "AXISBANK",
    "BAJFINANCE",
    "BAJAJFINSV",
    "BHARTIARTL",
    "HCLTECH",
    "HDFCBANK",
    "HINDUNILVR",
    "ICICIBANK",
    "INFY",
    "ITC",
    "KOTAKBANK",
    "LT",
    "M&M",
    "MARUTI",
    "NESTLEIND",
    "NTPC",
    "POWERGRID",
    "RELIANCE",
    "SBIN",
    "SUNPHARMA",
    "TCS",
    "TATAMOTORS",
    "TATASTEEL",
    "TECHM",
    "TITAN",
    "ULTRACEMCO",
    "WIPRO",
    "INDUSINDBK",
    "JSWSTEEL",
)

INDEX_MEMBERS = {
    "NIFTY": (NIFTY_50, "NSE_EQ"),
    "BANKNIFTY": (BANKNIFTY, "NSE_EQ"),
    "SENSEX": (SENSEX, "BSE_EQ"),
}


def _pick(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        val = (row.get(key) or "").strip()
        if val:
            return val
    upper = {str(k).upper(): k for k in row}
    for key in keys:
        real = upper.get(key.upper())
        if real and str(row.get(real) or "").strip():
            return str(row.get(real)).strip()
    return ""


def parse_equity_ids(csv_text: str, symbols: set[str], *, prefer_segment: str) -> dict[str, tuple[str, str]]:
    """Map SYMBOL -> (security_id, segment). First EQ match wins."""
    reader = csv.DictReader(io.StringIO(csv_text))
    header = [str(h) for h in (reader.fieldnames or [])]
    id_col = None
    for cand in (
        "SECURITY_ID",
        "SEM_SMST_SECURITY_ID",
        "SEM_SECURITY_ID",
        "SMST_SECURITY_ID",
    ):
        if cand in header:
            id_col = cand
            break
    want = {s.upper() for s in symbols}
    found: dict[str, tuple[str, str]] = {}
    for row in reader:
        inst = _pick(row, "INSTRUMENT", "SEM_INSTRUMENT_NAME", "INSTRUMENT_TYPE").upper()
        series = _pick(row, "SERIES", "SEM_SERIES").upper()
        if inst and inst not in {"EQUITY", "EQ", "ES", ""}:
            continue
        if series and series not in {"EQ", "A", "B", "T", ""}:
            continue
        sym = _pick(
            row,
            "UNDERLYING_SYMBOL",
            "SEM_TRADING_SYMBOL",
            "SM_SYMBOL_NAME",
            "SYMBOL_NAME",
        ).upper()
        if sym not in want or sym in found:
            continue
        sid = (row.get(id_col) if id_col else "") or _pick(
            row, "SECURITY_ID", "SEM_SMST_SECURITY_ID", "SEM_SECURITY_ID"
        )
        if not sid:
            continue
        exch = _pick(row, "EXCH_ID", "SEM_EXM_EXCH_ID").upper()
        if prefer_segment == "NSE_EQ" and exch.startswith("BSE"):
            continue
        if prefer_segment == "BSE_EQ" and exch.startswith("NSE"):
            continue
        segment = prefer_segment
        if exch.startswith("BSE"):
            segment = "BSE_EQ"
        elif exch.startswith("NSE"):
            segment = "NSE_EQ"
        found[sym] = (str(sid), segment)
    return found


def ltp_from_quote(payload: Any) -> dict[tuple[str, str], float]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        data = payload if isinstance(payload, dict) else {}
    out: dict[tuple[str, str], float] = {}
    for seg, blob in data.items():
        if not isinstance(blob, dict):
            continue
        for sid, cell in blob.items():
            raw: Optional[Any]
            if isinstance(cell, dict):
                raw = cell.get("last_price") or cell.get("LTP") or cell.get("ltp")
            else:
                raw = cell
            try:
                out[(str(seg), str(sid))] = float(raw)
            except (TypeError, ValueError):
                continue
    return out
