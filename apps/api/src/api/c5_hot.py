"""C5-05 cheap paper-customer reads. No Dhan. No founder overlay. No live broker.

Hot paths for five paper seats:
- list signals (signals:public tail)
- account status (this seat only)
- journal / tape tail (last public envelopes + last tape line)

Founder desk snapshot, ledger scans, and port probes stay off this module.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

IST = timezone(timedelta(hours=5, minutes=30))
REPO = Path(__file__).resolve().parents[4]
SIGNAL_FIELDS = (
    "underlying",
    "side",
    "decision",
    "trend",
    "chain_3m",
    "news",
    "cited_news",
)
SIGNALS_KEEP = 16
JOURNAL_KEEP = 20
TAPE_READ_BYTES = 8192
PUBLIC = "signals:public"

_REG_LOCK = threading.Lock()
_REG_CACHE: Optional[tuple[tuple[int, int, str], Any]] = None


def _ist_now() -> str:
    dt = datetime.now(IST)
    text = dt.isoformat(timespec="milliseconds")
    return text if text.endswith("+05:30") else dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+05:30"


def resolve_paper_account_id(sub: Optional[str]) -> Optional[str]:
    """Map a paper login sub (c1 or customer-01) to the isolated book id."""
    raw = (sub or "").strip()
    if not raw:
        return None
    if raw.startswith("customer-") and raw[9:].isdigit():
        return raw
    if len(raw) >= 2 and raw[0] in {"c", "C"} and raw[1:].isdigit():
        n = int(raw[1:])
        if 1 <= n <= 5:
            return f"customer-{n:02d}"
    return raw


def compact_signal(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    payload = item.get("payload")
    src = payload if isinstance(payload, dict) else item
    return {k: src[k] for k in SIGNAL_FIELDS if k in src and src[k] is not None}


def _public_items(hub: Any, keep: int) -> tuple[list[Any], int]:
    data = hub.snapshot_channel(PUBLIC, "customer")
    items = list(data.get("items") or [])
    if keep > 0:
        items = items[-keep:]
    return items, int(data.get("seq") or 0)


def list_signals(hub: Any) -> dict[str, Any]:
    """Last N public signals. Reuses hub seq so five seats share one body."""
    cached = getattr(hub, "_c5_sig_cache", None)
    items, seq = _public_items(hub, SIGNALS_KEEP)
    if cached and cached[0] == seq:
        return cached[1]
    compact = [compact_signal(it) for it in items]
    body = {
        "ok": True,
        "as_of": _ist_now(),
        "role": "customer",
        "channels": {PUBLIC: {"seq": seq, "items": items}},
        "denied": [],
        "positions": [],
        "traces": {},
        "signals": compact,
        "n": len(compact),
        "seq": seq,
        "orders": "REFUSED",
        "promote": False,
        "v2": True,
    }
    hub._c5_sig_cache = (seq, body)
    return body


def _registry() -> Any:
    """Load accounts.yaml once per (mtime, size). Fail closed on live/unknown."""
    global _REG_CACHE
    from accounts.registry import AccountRegistry, default_config_path

    path = default_config_path()
    try:
        st = path.stat()
        stamp = (st.st_mtime_ns, st.st_size, str(path))
    except OSError:
        stamp = (0, 0, str(path))
    hit = _REG_CACHE
    if hit and hit[0] == stamp:
        return hit[1]
    with _REG_LOCK:
        hit = _REG_CACHE
        if hit and hit[0] == stamp:
            return hit[1]
        registry = AccountRegistry.load(path)
        _REG_CACHE = (stamp, registry)
        return registry


def account_status(sub: Optional[str]) -> dict[str, Any]:
    """This paper seat only. Never lists the other four books."""
    aid = resolve_paper_account_id(sub)
    if aid is None:
        return {
            "ok": True,
            "role": "customer",
            "account_id": None,
            "status": "paper-seat",
            "kind": "customer",
            "broker": "paper",
            "active": False,
            "note": "localhost paper label; no isolated book bound",
            "orders": "REFUSED",
            "live_broker": False,
            "promote": False,
        }
    try:
        acc = _registry().get(aid)
    except Exception as exc:  # noqa: BLE001 — fail closed; do not leak siblings
        return {
            "ok": False,
            "role": "customer",
            "account_id": aid,
            "code": str(exc).split(":", 1)[0] or "UNKNOWN_ACCOUNT",
            "orders": "REFUSED",
            "live_broker": False,
            "promote": False,
        }
    if acc.kind != "customer":
        return {
            "ok": False,
            "role": "customer",
            "account_id": aid,
            "code": "CUSTOMER_ONLY",
            "orders": "REFUSED",
            "live_broker": False,
            "promote": False,
        }
    return {
        "ok": True,
        "role": "customer",
        "account_id": acc.account_id,
        "kind": acc.kind,
        "broker": acc.broker,
        "status": acc.status,
        "active": acc.status == "active",
        "risk_budget_inr": acc.risk_budget_inr,
        "orders": "REFUSED",
        "live_broker": False,
        "promote": False,
    }


def _today_tape() -> Optional[Path]:
    day = datetime.now(IST).date().isoformat()
    dual = REPO / "data" / "recon" / "paper_watch" / "DUAL-TAPE" / f"{day}.jsonl"
    if dual.is_file():
        return dual
    v2 = REPO / "data" / "tape" / "v2" / day / "quote_snapshots.jsonl"
    if v2.is_file():
        return v2
    return None


def last_tape_line(path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Seek the last ~8 KiB of today's tape. Never scan the whole file."""
    target = path if path is not None else _today_tape()
    if target is None:
        return None
    try:
        size = target.stat().st_size
        with target.open("rb") as fh:
            if size > TAPE_READ_BYTES:
                fh.seek(size - TAPE_READ_BYTES)
            chunk = fh.read()
    except OSError:
        return None
    for raw in reversed(chunk.splitlines()):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if isinstance(row, dict):
            return {
                "as_of_ist": row.get("as_of_ist") or row.get("as_of"),
                "source": target.name,
            }
    return None


def journal_tail(hub: Any, *, n: int = JOURNAL_KEEP) -> dict[str, Any]:
    keep = max(1, min(int(n), JOURNAL_KEEP))
    items, seq = _public_items(hub, keep)
    tape = last_tape_line()
    return {
        "ok": True,
        "as_of": _ist_now(),
        "role": "customer",
        "items": [compact_signal(it) for it in items],
        "n": len(items),
        "seq": seq,
        "tape_last": tape,
        "orders": "REFUSED",
        "promote": False,
        "v2": True,
    }


__all__ = [
    "JOURNAL_KEEP",
    "PUBLIC",
    "SIGNALS_KEEP",
    "account_status",
    "compact_signal",
    "journal_tail",
    "last_tape_line",
    "list_signals",
    "resolve_paper_account_id",
]
