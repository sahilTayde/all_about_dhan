"""Async compact LLM counsel. Fail-soft; never blocks NEW open.

ALLOW is in the architecture: observer ALLOW may fire allow-review, but the
desk fill does not wait on HTTP. Empty GEMINI/OPENAI → mock. Never prints
secrets. Does not invent CE/PE. NO_PROMOTE.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

JOB_EXIT = "exit-review"
JOB_RISK = "risk-review"
JOB_PARTIAL = "partial-book-review"
JOB_ALLOW = "allow-review"
JOBS = (JOB_EXIT, JOB_RISK, JOB_PARTIAL, JOB_ALLOW)

INSTR_WAIT = "wait"
INSTR_TRAIL = "trail after T1"
INSTR_SHIFT = "shift T1"
INSTR_CUT = "cut"

MOCK_BY_JOB = {
    JOB_EXIT: INSTR_WAIT,
    JOB_RISK: INSTR_WAIT,
    JOB_PARTIAL: INSTR_TRAIL,
    JOB_ALLOW: INSTR_WAIT,
}


def keys_present() -> dict[str, bool]:
    gem = bool((os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY") or "").strip())
    oai = bool((os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or "").strip())
    return {"gemini": gem, "openai": oai}


def mock_counsel(job: str, compact: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Deterministic fixture. No HTTP. Does not invent CE/PE."""
    jid = job if job in JOBS else JOB_RISK
    instruction = MOCK_BY_JOB[jid]
    side = None
    if isinstance(compact, dict):
        side = compact.get("side") if compact.get("side") in {"CE", "PE"} else None
    return {
        "ok": True,
        "mock": True,
        "job": jid,
        "instruction": instruction,
        "side": side,
        "provider": "mock",
        "blocked_open": False,
        "promote": False,
        "note": "Mock LLM. Fast path must not wait on this. NO_PROMOTE.",
    }


def overlay_to_boss(
    *,
    open_pos: Optional[dict[str, Any]] = None,
    itm_bin: Optional[dict[str, Any]] = None,
    ml_overlay: Optional[dict[str, Any]] = None,
    classified: Optional[dict[str, Any]] = None,
    trigger: Optional[str] = None,
) -> dict[str, Any]:
    """Desk states the open book to boss. Rules default = wait. Not a fill."""
    pos = dict(open_pos or {})
    bin_pkt = dict(itm_bin or {})
    ml = dict(ml_overlay or {})
    if ml.get("side") in {"CE", "PE"}:
        ml = {**ml, "side": None, "note": "KMeans is not BUY_CE"}
    instruction = INSTR_WAIT
    if trigger in {"STOP", "CANCEL_AGAINST", "CANCEL_STALL"}:
        instruction = INSTR_CUT
    elif trigger in {"TARGET", "T1"}:
        instruction = INSTR_TRAIL
    return {
        "promote": False,
        "open": {
            "book_id": pos.get("book_id"),
            "underlying": pos.get("underlying"),
            "side": pos.get("side"),
            "filled": pos.get("filled"),
            "entry": pos.get("entry"),
            "stop": pos.get("stop"),
            "target": pos.get("target"),
            "agent_status": pos.get("agent_status"),
        },
        "itm_bin": bin_pkt,
        "classified": {
            "regime": (classified or {}).get("regime"),
            "direction": (classified or {}).get("direction"),
        },
        "ml_overlay": {
            "hold": bool(ml.get("hold")),
            "regime": ml.get("regime"),
            "residual": ml.get("residual"),
            "note": ml.get("note") or "HOLD/regime/residual advice, not BUY_CE",
        },
        "trigger": trigger,
        "boss_instruction": instruction,
        "llm_review": None,
        "note": "Review path. Does not block NEW. Booking overlay unchanged.",
    }


def compact_counsel(
    job: str,
    compact: dict[str, Any],
    *,
    force_mock: bool = False,
    complete_fn: Optional[Callable[..., dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Counsel on review jobs and ALLOW. Does not pick CE/PE. Fail-soft on missing keys/HTTP."""
    present = keys_present()
    if force_mock or not (present["gemini"] or present["openai"]):
        return mock_counsel(job, compact)
    if complete_fn is None:
        return {
            **mock_counsel(job, compact),
            "ok": False,
            "mock": True,
            "instruction": INSTR_WAIT,
            "gap": "DATA_INSUFFICIENT: counsel complete_fn not wired on review path",
            "note": "Fail-soft wait. Fast path already opened or skipped. NO_PROMOTE.",
        }
    try:
        result = complete_fn(job=job, compact=compact)
    except Exception as exc:  # noqa: BLE001
        return {
            **mock_counsel(job, compact),
            "ok": False,
            "mock": True,
            "instruction": INSTR_WAIT,
            "gap": f"DATA_INSUFFICIENT: counsel {type(exc).__name__}",
            "note": "Fail-soft wait. Keys not echoed. NO_PROMOTE.",
        }
    text = str((result or {}).get("text") or "").lower()
    instruction = INSTR_WAIT
    if "cut" in text or "flatten" in text or "kill" in text:
        instruction = INSTR_CUT
    elif "shift" in text:
        instruction = INSTR_SHIFT
    elif "trail" in text:
        instruction = INSTR_TRAIL
    out = {
        "ok": bool((result or {}).get("ok")),
        "mock": False,
        "job": job if job in JOBS else JOB_RISK,
        "instruction": instruction,
        "side": compact.get("side") if compact.get("side") in {"CE", "PE"} else None,
        "provider": (result or {}).get("provider"),
        "blocked_open": False,
        "promote": False,
    }
    if not out["ok"]:
        out["instruction"] = INSTR_WAIT
        out["gap"] = str((result or {}).get("gap") or "DATA_INSUFFICIENT")
        out["mock"] = True
    return out


def maybe_llm_review(
    *,
    trigger: Optional[str],
    compact: dict[str, Any],
    observer_action: Optional[str] = None,
    opened_this_tick: bool = False,
    force_mock: bool = True,
) -> Optional[dict[str, Any]]:
    """ALLOW fires allow-review (non-blocking). Other jobs skip the NEW open tick."""
    if observer_action == "ALLOW" or trigger in {"ALLOW", JOB_ALLOW}:
        out = compact_counsel(JOB_ALLOW, compact, force_mock=force_mock)
        out["blocked_open"] = False
        return out
    if opened_this_tick:
        return None
    if trigger not in {
        "STOP",
        "CANCEL_STALL",
        "CANCEL_AGAINST",
        "TARGET",
        "T1",
        "1M_CLOSE",
        JOB_EXIT,
        JOB_RISK,
        JOB_PARTIAL,
    }:
        return None
    job = JOB_EXIT
    if trigger in {JOB_RISK, "CANCEL_AGAINST", "STOP"}:
        job = JOB_RISK
    elif trigger in {JOB_PARTIAL, "TARGET", "T1"}:
        job = JOB_PARTIAL
    elif trigger in {JOB_EXIT, "CANCEL_STALL", "1M_CLOSE"}:
        job = JOB_EXIT
    return compact_counsel(job, compact, force_mock=force_mock)
