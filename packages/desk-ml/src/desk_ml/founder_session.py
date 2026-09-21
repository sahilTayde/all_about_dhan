"""Founder picks which indices may get NEW paper fills today.

Dual-tape still records every index for replay. Boss / dealer / analysts
do not choose the book. An already-OPEN ticket is never flattened here.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from desk_ml.persist import repo_root

KNOWN = ("NIFTY", "BANKNIFTY", "SENSEX")
DEFAULT = ("NIFTY",)
FILE_NAME = "founder_trade_underlyings.json"
STOP_REASON = "FOUNDER_STOP_TRADING_ON_INDEX"
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
        stopped = [n for n in KNOWN if n not in DEFAULT]
        return {
            "ok": True,
            "trade_underlyings": list(DEFAULT),
            "stopped_underlyings": stopped,
            "known_underlyings": list(KNOWN),
            "apply_new_fills_only": True,
            "tape_records_all": True,
            "source": "default",
            "orders": "REFUSED",
            "promote": False,
        }
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        stopped = [n for n in KNOWN if n not in DEFAULT]
        return {
            "ok": False,
            "trade_underlyings": list(DEFAULT),
            "stopped_underlyings": stopped,
            "known_underlyings": list(KNOWN),
            "apply_new_fills_only": True,
            "tape_records_all": True,
            "source": "unreadable",
            "orders": "REFUSED",
            "promote": False,
        }
    names = _clean(blob.get("trade_underlyings") if "trade_underlyings" in blob else DEFAULT)
    stopped = [n for n in KNOWN if n not in names]
    return {
        "ok": True,
        "trade_underlyings": names,
        "stopped_underlyings": stopped,
        "known_underlyings": list(KNOWN),
        "apply_new_fills_only": True,
        "tape_records_all": True,
        "as_of_ist": blob.get("as_of_ist"),
        "source": "file",
        "orders": "REFUSED",
        "promote": False,
        "note": blob.get("note")
        or "Founder book for NEW paper fills. Dual-tape still captures all indices.",
    }


def save_founder_book(names: Iterable[Any], *, root: Optional[Path] = None) -> dict[str, Any]:
    cleaned = _clean(names)
    payload = {
        "ok": True,
        "trade_underlyings": cleaned,
        "stopped_underlyings": [n for n in KNOWN if n not in cleaned],
        "known_underlyings": list(KNOWN),
        "apply_new_fills_only": True,
        "tape_records_all": True,
        "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
        "source": "file",
        "orders": "REFUSED",
        "promote": False,
        "note": "Founder book for NEW paper fills only. Open tickets stay. Dual-tape records all.",
    }
    path = session_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


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
