"""Resolve nearest index-futures security IDs from the public scrip-master CSV.

Do not hardcode NIFTY/BANKNIFTY/SENSEX FUTIDX IDs. Filter the live CSV.
Compact vs detailed headers differ — inspect the header, then match columns.
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Optional

from dhan_client.instruments import first_security_id_column

INDEX_UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")

# Exact underlying tokens we accept. Reject NIFTYNXT / FINNIFTY / BANKEX / etc.
_ACCEPT = {
    "NIFTY": frozenset({"NIFTY", "NIFTY 50", "NIFTY50"}),
    "BANKNIFTY": frozenset({"BANKNIFTY", "NIFTY BANK", "NIFTYBANK", "BANK NIFTY"}),
    "SENSEX": frozenset({"SENSEX"}),
}

_SEG_HINT = {
    "NIFTY": "NSE_FNO",
    "BANKNIFTY": "NSE_FNO",
    "SENSEX": "BSE_FNO",
}

_REJECT_SUBSTR = (
    "NIFTYNXT",
    "FINNIFTY",
    "MIDCPNIFTY",
    "BANKEX",
    "SENSEX50",
    "NIFTYIT",
)


@dataclass(frozen=True)
class FutIdxContract:
    underlying: str
    security_id: str
    exchange_segment: str
    expiry: str
    symbol: str
    instrument: str = "FUTIDX"


def _norm(value: object) -> str:
    return str(value or "").strip().upper().replace("_", " ")


def _parse_expiry(raw: str) -> Optional[date]:
    text = str(raw or "").strip()
    if not text:
        return None
    if len(text) >= 10 and text[4] == "-":
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            pass
    for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19] if fmt.endswith("%S") else text, fmt).date()
        except ValueError:
            continue
    return None


def _pick(row: dict[str, str], *names: str) -> str:
    lower = {k.lower(): v for k, v in row.items() if k}
    for name in names:
        if name.lower() in lower:
            return str(lower[name.lower()] or "").strip()
    return ""


def _is_futidx(row: dict[str, str]) -> bool:
    inst = _norm(
        _pick(
            row,
            "SEM_INSTRUMENT_NAME",
            "INSTRUMENT",
            "INSTRUMENT_TYPE",
            "SEM_EXCH_INSTRUMENT_TYPE",
        )
    )
    return inst.replace(" ", "") in {"FUTIDX", "INDEXFUTURES", "FUT IDX"}


_REJECT_UNDERLYING = frozenset(
    {
        "NIFTYFPI",
        "NIFTYNXT50",
        "NIFTYNXT",
        "FINNIFTY",
        "MIDCPNIFTY",
        "BANKEX",
        "SENSEX50",
        "NIFTYIT",
    }
)


def _underlying_match(row: dict[str, str]) -> Optional[str]:
    und = _norm(_pick(row, "UNDERLYING_SYMBOL"))
    if und in _ACCEPT["NIFTY"]:
        return "NIFTY"
    if und in _ACCEPT["BANKNIFTY"]:
        return "BANKNIFTY"
    if und in _ACCEPT["SENSEX"]:
        return "SENSEX"
    if und in _REJECT_UNDERLYING:
        return None
    blob = " ".join(
        [
            _pick(row, "UNDERLYING_SYMBOL", "SM_SYMBOL_NAME", "SEM_TRADING_SYMBOL"),
            _pick(row, "SYMBOL_NAME", "DISPLAY_NAME", "SEM_CUSTOM_SYMBOL"),
        ]
    )
    joined = _norm(blob)
    compact = joined.replace(" ", "")
    for bad in _REJECT_SUBSTR:
        if bad in compact:
            return None
    if compact.startswith("NIFTYFPI") or "NIFTYFPI" in compact:
        return None
    # Compact CSV fallback: "NIFTY SEP FUT" / "NIFTY 29 SEP FUT"
    if joined.startswith("NIFTY ") and "FUT" in joined and "BANK" not in joined:
        return "NIFTY"
    if "BANKNIFTY" in compact and "FUT" in joined:
        return "BANKNIFTY"
    if joined.startswith("SENSEX") and "FUT" in joined:
        return "SENSEX"
    return None


def _segment(row: dict[str, str], underlying: str) -> str:
    raw = _pick(
        row,
        "SEGMENT",
        "SEM_SEGMENT",
        "EXCH_ID",
        "SEM_EXM_EXCH_ID",
    )
    upper = _norm(raw).replace(" ", "_")
    if "BSE" in upper and ("FNO" in upper or "FO" in upper or "F&O" in upper):
        return "BSE_FNO"
    if "NSE" in upper and ("FNO" in upper or "FO" in upper or "F&O" in upper):
        return "NSE_FNO"
    if upper in {"NSE_FNO", "BSE_FNO"}:
        return upper
    return _SEG_HINT[underlying]


def _iter_futidx_rows(text: str) -> list[tuple[str, date, FutIdxContract]]:
    """Every listed NIFTY / BANKNIFTY / SENSEX FUTIDX row, including expired."""
    reader = csv.DictReader(io.StringIO(text))
    header = list(reader.fieldnames or [])
    id_col = first_security_id_column(header)
    out: list[tuple[str, date, FutIdxContract]] = []
    for row in reader:
        if not _is_futidx(row):
            continue
        underlying = _underlying_match(row)
        if underlying is None:
            continue
        sid = ""
        if id_col:
            sid = str(row.get(id_col) or "").strip()
        if not sid:
            sid = _pick(row, *["SECURITY_ID", "SEM_SMST_SECURITY_ID", "SEM_SECURITY_ID"])
        if not sid:
            continue
        expiry_raw = _pick(row, "SM_EXPIRY_DATE", "SEM_EXPIRY_DATE", "EXPIRY_DATE")
        expiry = _parse_expiry(expiry_raw)
        if expiry is None:
            continue
        symbol = _pick(row, "SEM_CUSTOM_SYMBOL", "DISPLAY_NAME", "SYMBOL_NAME", "SM_SYMBOL_NAME")
        contract = FutIdxContract(
            underlying=underlying,
            security_id=str(sid),
            exchange_segment=_segment(row, underlying),
            expiry=expiry.isoformat(),
            symbol=symbol or f"{underlying} FUT",
        )
        out.append((underlying, expiry, contract))
    return out


def parse_all_futidx_csv(text: str) -> dict[str, list[FutIdxContract]]:
    """All listed contracts per underlying, nearest expiry first. Not nearest-only."""
    grouped: dict[str, list[tuple[date, FutIdxContract]]] = {
        "NIFTY": [],
        "BANKNIFTY": [],
        "SENSEX": [],
    }
    for underlying, expiry, contract in _iter_futidx_rows(text):
        grouped[underlying].append((expiry, contract))
    out: dict[str, list[FutIdxContract]] = {}
    for name, rows in grouped.items():
        rows.sort(key=lambda item: item[0])
        # de-dupe security_id, keep first (nearest expiry)
        seen: set[str] = set()
        contracts: list[FutIdxContract] = []
        for _exp, contract in rows:
            if contract.security_id in seen:
                continue
            seen.add(contract.security_id)
            contracts.append(contract)
        if contracts:
            out[name] = contracts
    return out


def parse_futidx_csv(text: str, *, as_of: Optional[date] = None) -> dict[str, FutIdxContract]:
    """Pick the nearest unexpired FUTIDX per underlying from CSV text."""
    as_of = as_of or date.today()
    best: dict[str, tuple[date, FutIdxContract]] = {}
    for underlying, expiry, contract in _iter_futidx_rows(text):
        if expiry < as_of:
            continue
        prev = best.get(underlying)
        if prev is None or expiry < prev[0]:
            best[underlying] = (expiry, contract)
    return {k: v[1] for k, v in best.items()}


def contracts_as_dicts(contracts: dict[str, FutIdxContract]) -> list[dict[str, str]]:
    return [asdict(c) for c in contracts.values()]
