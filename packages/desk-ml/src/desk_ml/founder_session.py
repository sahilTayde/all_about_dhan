"""Founder picks which indices may get NEW paper fills today.

Dual-tape still records every index for replay. Boss / dealer / analysts
do not choose the book. An already-OPEN ticket is never flattened here.

Human manage of an OPEN paper fill (required TARGET + STOP, SET_LEVELS) lives
in desk_ml.paper_scalp.save_human_override — not a naked EXIT.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from desk_ml.persist import repo_root

KNOWN = ("NIFTY", "BANKNIFTY", "SENSEX")
# Default STOP TRADE on every index. Founder START is the only way NEW fills begin.
DEFAULT: tuple[str, ...] = ()
FILE_NAME = "founder_trade_underlyings.json"
STOP_REASON = "FOUNDER_STOP_TRADING_ON_INDEX"
START_ACTION = "START"
STOP_ACTION = "STOP"
IST = ZoneInfo("Asia/Kolkata")


def session_path(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / "data" / "recon" / FILE_NAME


def _clean(names: Iterable[Any]) -> list[str]:
    out: list[str] = []
    for raw in names or []:
        u = str(raw or "").strip().upper().replace(" ", "")
        if u in KNOWN and u not in out:
            out.append(u)
    return out


def load_founder_book(root: Optional[Path] = None) -> dict[str, Any]:
    path = session_path(root)
    if not path.is_file():
        return _payload(list(DEFAULT), source="default")
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _payload(list(DEFAULT), source="unreadable", ok=False)
    names = _clean(blob.get("trade_underlyings") if "trade_underlyings" in blob else DEFAULT)
    return _payload(
        names,
        source="file",
        as_of_ist=blob.get("as_of_ist"),
        note=blob.get("note"),
    )


def _index_status(names: list[str]) -> dict[str, str]:
    started = set(names)
    return {n: (START_ACTION if n in started else STOP_ACTION) for n in KNOWN}


def _payload(
    names: list[str],
    *,
    source: str,
    ok: bool = True,
    as_of_ist: Any = None,
    note: Any = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "trade_underlyings": names,
        "stopped_underlyings": [n for n in KNOWN if n not in names],
        "known_underlyings": list(KNOWN),
        "index_status": _index_status(names),
        "apply_new_fills_only": True,
        "tape_records_all": True,
        "default_action": STOP_ACTION,
        "as_of_ist": as_of_ist,
        "source": source,
        "orders": "REFUSED",
        "promote": False,
        "note": note
        or "Founder START/STOP per index. Default STOP TRADE. Dual-tape still records all.",
    }


def save_founder_book(names: Iterable[Any], *, root: Optional[Path] = None) -> dict[str, Any]:
    payload = _payload(
        _clean(names),
        source="file",
        as_of_ist=datetime.now(IST).isoformat(timespec="seconds"),
        note="Founder START/STOP for NEW paper fills only. Open tickets stay. Dual-tape records all.",
    )
    path = session_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def set_index_trade(underlying: Any, action: Any, *, root: Optional[Path] = None) -> dict[str, Any]:
    """START or STOP NEW fills on one index. Other indices keep their state."""
    u = str(underlying or "").strip().upper().replace(" ", "")
    act = str(action or "").strip().upper()
    if act in {"START TRADE", "START_TRADE", "RESTART"}:
        act = START_ACTION
    if act in {"STOP TRADE", "STOP_TRADE"}:
        act = STOP_ACTION
    if u not in KNOWN:
        book = load_founder_book(root)
        book["ok"] = False
        book["error"] = "UNKNOWN_UNDERLYING"
        return book
    if act not in {START_ACTION, STOP_ACTION}:
        book = load_founder_book(root)
        book["ok"] = False
        book["error"] = "UNKNOWN_ACTION"
        return book
    loaded = load_founder_book(root)
    names = list(loaded.get("trade_underlyings") or [])
    if loaded.get("source") != "file":
        names = list(DEFAULT)
    if act == START_ACTION:
        if u not in names:
            names.append(u)
    else:
        names = [n for n in names if n != u]
    saved = save_founder_book(names, root=root)
    saved["last_underlying"] = u
    saved["last_action"] = act
    return saved


def allows_new_fill(underlying: str, *, root: Optional[Path] = None) -> bool:
    book = load_founder_book(root)
    names = book.get("trade_underlyings") if "trade_underlyings" in book else list(DEFAULT)
    return str(underlying or "").upper() in set(names or [])


def new_fill_decision(underlying: str, *, root: Optional[Path] = None) -> dict[str, Any]:
    u = str(underlying or "").upper()
    allow = allows_new_fill(u, root=root)
    return {
        "allow": allow,
        "underlying": u,
        "reason": None if allow else STOP_REASON,
        "note": "Tape still records this index; founder stopped NEW paper fills only.",
    }
