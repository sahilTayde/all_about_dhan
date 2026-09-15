"""Paper overlay attach: dual-tape ticks → HOLD/WATCH. No orders. No MIX writes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Sequence

from desk_ml.fit import score_last
from desk_ml.mrr import score_mrr_last
from desk_ml.persist import repo_root
from desk_ml.tape import load_dual_tape_triples, thin_hold

SESSION_UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")


def score_one(
    underlying: str,
    *,
    root: Optional[Path] = None,
    source: str = "dual-tape",
) -> dict[str, Any]:
    base = root or repo_root()
    src = (source or "cache").strip().lower()
    if src in {"dual-tape", "dual_tape", "live-paper"}:
        triples, tape = load_dual_tape_triples(underlying, root=base)
        if len(triples) < 2:
            return thin_hold(
                underlying=underlying,
                reason="DATA_INSUFFICIENT: need ≥2 dual-tape ticks with INDEX+ATM CE+PE LTP",
                tape=tape,
            )
    ml001 = score_last(underlying, root=base, source=source)
    if not ml001.get("ok"):
        hold = thin_hold(
            underlying=underlying,
            reason=str(ml001.get("reason") or ml001.get("status") or "score failed"),
            tape=ml001.get("tape") if isinstance(ml001.get("tape"), dict) else {},
        )
        hold["ml001"] = ml001
        return hold
    mrr = score_mrr_last(underlying, root=base, source=source)
    follow = bool(ml001.get("follow_gap")) or bool(mrr.get("follow_gap"))
    thin_mrr = (not mrr.get("ok")) and str(mrr.get("status") or "") == "DATA_INSUFFICIENT"
    session = "HOLD" if follow or thin_mrr or ml001.get("session_action") == "HOLD" else str(ml001.get("session_action") or "WATCH_ONLY")
    return {
        "ok": True,
        "underlying": underlying.upper(),
        "ml001": {
            k: ml001.get(k)
            for k in (
                "ok",
                "status",
                "overlay",
                "reason_code",
                "follow_gap",
                "session_action",
                "allow_new_paper_ce_pe",
                "premium_divergence",
                "regime",
            )
        },
        "ml002": {
            k: mrr.get(k)
            for k in (
                "ok",
                "status",
                "overlay",
                "follow_gap",
                "session_action",
                "reason_code",
                "window",
            )
        },
        "follow_gap": follow,
        "session_action": session,
        "allow_new_paper_ce_pe": session != "HOLD",
        "promote": False,
        "production_params_written": False,
        "execution": "refused",
        "oos_claim": False,
        "win_rate": None,
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
    }


def score_session(
    *,
    root: Optional[Path] = None,
    underlyings: Sequence[str] = SESSION_UNDERLYINGS,
    source: str = "dual-tape",
) -> dict[str, Any]:
    base = root or repo_root()
    rows = {u: score_one(u, root=base, source=source) for u in underlyings}
    any_hold = any(r.get("session_action") == "HOLD" for r in rows.values())
    report = {
        "ok": True,
        "job": "PAPER_OVERLAY",
        "underlyings": list(underlyings),
        "source": source,
        "rows": rows,
        "session_action": "HOLD" if any_hold else "WATCH_ONLY",
        "promote": False,
        "production_params_written": False,
        "execution": "refused",
        "oos_claim": False,
        "cpcv": False,
        "win_rate": None,
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "research_ready_for_programming": False,
        "note": "Paper overlay only. HOLD on FOLLOW-GAP or thin ticks. Not a five-pass.",
    }
    return report


def attach_after_tick(repo: Path, mix_dir: Path, *, underlyings: Sequence[str] = SESSION_UNDERLYINGS) -> Optional[Path]:
    """Called from dual-tape persist. Fail-soft. Never orders."""
    report = score_session(root=repo, underlyings=underlyings, source="dual-tape")
    mix_dir.mkdir(parents=True, exist_ok=True)
    path = mix_dir / "overlay_last.json"
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return path
