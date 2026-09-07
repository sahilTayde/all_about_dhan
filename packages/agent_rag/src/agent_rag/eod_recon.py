"""EOD reconciliation stub — paper ledger → session tag → RETUNE_PROPOSAL.

No auto-retune. No production param writes. Aligns EVENT_MEMORY / RETUNE_GATE.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agent_rag.paths import load_dotenv, repo_root


def _ist_today() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc).date().isoformat()


def _load_ledger(root: Path, day: str) -> dict[str, Any]:
    path = root / "data" / "desk_intel" / "ledger" / day / "ledger.json"
    if not path.is_file():
        return {
            "day": day,
            "note": "DATA_INSUFFICIENT — no paper ledger for day",
            "users": {},
            "records": [],
            "missing": True,
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"day": day, "error": "JSON_DECODE", "records": [], "missing": True}
    if not isinstance(raw, dict):
        return {"day": day, "error": "NOT_OBJECT", "records": [], "missing": True}
    raw["missing"] = False
    return raw


def _load_nightly_recon(root: Path, day: str) -> Optional[dict[str, Any]]:
    path = root / "data" / "recon" / f"{day}.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return raw if isinstance(raw, dict) else None


def _load_candidate_audit(root: Path, day: str) -> dict[str, Any]:
    """Summarize PAPER candidate observations without deriving marks or P/L."""
    path = root / "data" / "recon" / "paper_ledger" / f"{day}.jsonl"
    if not path.is_file():
        return {
            "missing": True,
            "observation_count": 0,
            "note": "DATA_INSUFFICIENT — no candidate audit mirror for day",
        }
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("event_type") == "CANDIDATE_OBSERVATION":
                    rows.append(row)
    except (OSError, json.JSONDecodeError):
        return {
            "missing": True,
            "observation_count": 0,
            "note": "DATA_INSUFFICIENT — candidate audit mirror unreadable",
        }
    outcomes = Counter(str(row.get("outcome")) for row in rows)
    return {
        "missing": False,
        "observation_count": len(rows),
        "candidate_ids": sorted({str(row.get("candidate_id")) for row in rows}),
        "outcome_counts": dict(sorted(outcomes.items())),
        "marks_available": any(
            row.get("outcome") in {"ACHIEVED", "STOPPED", "INVALIDATED", "LOST"}
            for row in rows
        ),
        "pnl_available": False,
        "note": (
            "PAPER observations only; marks and P/L are absent unless an "
            "authoritative mark adapter appends them."
        ),
    }


def _classify_session(
    *,
    day: str,
    ledger: dict[str, Any],
    nightly: Optional[dict[str, Any]],
    offline: bool,
) -> dict[str, Any]:
    """NORMAL vs NEWS_DAY / EXPIRY per EVENT_MEMORY philosophy (stub)."""
    if nightly and nightly.get("session_kind"):
        kind = str(nightly.get("session_kind"))
        flags = list(nightly.get("session_flags") or [kind])
        reasons = list(nightly.get("session_tag", {}).get("reasons") or [])
        if not reasons and nightly.get("session_reasons"):
            reasons = list(nightly["session_reasons"])
        return {
            "kind": kind,
            "flags": flags,
            "reasons": reasons or ["from nightly recon"],
            "usable_for_retune_sample": kind == "NORMAL",
            "score_track": "SCORE_SAMPLE" if kind == "NORMAL" else "ANALOG_MEMORY",
            "source": "nightly_recon",
        }

    # Offline / missing nightly: do not invent NEWS_DAY from empty calendar
    reasons = [
        "DATA_INSUFFICIENT: news calendar empty — cannot honestly tag NORMAL for SCORE_SAMPLE",
        "EVENT_MEMORY: without dated prints, day stays UNKNOWN for ranking",
    ]
    if offline:
        reasons.append("eod-recon --offline")
    if ledger.get("missing"):
        reasons.append("paper ledger missing for day")
    records = ledger.get("records") or []
    if records:
        reasons.append(f"ledger records={len(records)} (paper/shadow only)")

    return {
        "kind": "UNKNOWN",
        "flags": ["UNKNOWN"],
        "reasons": reasons,
        "usable_for_retune_sample": False,
        "score_track": "ANALOG_MEMORY",  # conservative: not SCORE_SAMPLE
        "source": "eod_stub",
        "note": (
            "Per EVENT_MEMORY: SCORE_SAMPLE requires NORMAL ∧ ¬CIRCUIT ∧ ¬GAP. "
            "Without a news calendar we refuse to claim NORMAL for ranking."
        ),
    }


def build_retune_proposal(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "RETUNE_PROPOSAL",
        "status": "BACKTEST_REQUIRED",
        "keep_current_strategy": True,
        "production_params_written": False,
        "handoff": "REVIEW",
        "backtest_owner": "06_backtesting",
        "session_kind": session.get("kind"),
        "session_flags": list(session.get("flags") or []),
        "session_usable_for_retune_sample": bool(
            session.get("usable_for_retune_sample")
        ),
        "oos_non_event_required": True,
        "metrics_required": ["expectancy", "profit_factor", "max_drawdown"],
        "one_day_pnl_is_not_evidence": True,
        "backtest_results": None,
        "candidate_notes": [
            "EOD stub only — do not auto-retune.",
            "Paper ledger P/L is not promote evidence.",
            f"score_track={session.get('score_track')}",
        ],
        "note": (
            "Default: keep current strategy. 06 must backtest OOS + NORMAL "
            "before any promote. Do not invent metrics."
        ),
    }


def _update_continue(root: Path, day: str, payload: dict[str, Any]) -> str:
    path = root / "teams" / "00_orchestrator" / "docs" / "CONTINUE_NEXT_CHAT.md"
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    marker = "### Agent RAG / EOD recon"
    block = "\n".join(
        [
            marker,
            "",
            f"**Last EOD stub:** {day} (`python -m agent_rag eod-recon`)",
            f"- session_kind: `{payload['session']['kind']}` "
            f"(score_track=`{payload['session'].get('score_track')}`)",
            f"- RETUNE_PROPOSAL: **`{payload['retune_proposal']['status']}`** "
            "(no auto-retune; `keep_current_strategy: true`)",
            f"- recon: `data/recon/EOD_RECON_{day}.json`",
            "- KB: `data/knowledge/agent_rag.sqlite` "
            "([`AGENT_RAG.md`](../../01_research/docs/AGENT_RAG.md)) — "
            "does **not** touch `transcripts.sqlite`",
            "- Paper agents backtest rollup: "
            f"[`BACKTEST_PAPER_AGENTS_{day}.md`]"
            f"(../../06_backtesting/docs/BACKTEST_PAPER_AGENTS_{day}.md) — "
            "**NO_PROMOTE**",
            "",
        ]
    )
    if marker in text:
        # Replace from marker through next ### or ## heading
        start = text.index(marker)
        rest = text[start:]
        cut = None
        for i, line in enumerate(rest.splitlines()[1:], start=1):
            if line.startswith("### ") or line.startswith("## "):
                cut = i
                break
        lines = text[:start].rstrip() + "\n\n" + block
        if cut is not None:
            after = "\n".join(rest.splitlines()[cut:])
            text = lines + "\n" + after
            if not text.endswith("\n"):
                text += "\n"
        else:
            text = lines if lines.endswith("\n") else lines + "\n"
    else:
        # Insert before "## Do not" if present
        anchor = "## Do not"
        if anchor in text:
            text = text.replace(anchor, block + anchor, 1)
        else:
            text = text.rstrip() + "\n\n" + block
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return str(path.relative_to(root))


def run_eod_recon(
    *,
    day: Optional[str] = None,
    root: Path | None = None,
    offline: bool = True,
    update_continue: bool = True,
) -> dict[str, Any]:
    load_dotenv()
    root = root or repo_root()
    day = day or _ist_today()
    ledger = _load_ledger(root, day)
    nightly = _load_nightly_recon(root, day)
    candidate_audit = _load_candidate_audit(root, day)
    session = _classify_session(
        day=day, ledger=ledger, nightly=nightly, offline=offline
    )
    proposal = build_retune_proposal(session)

    records = ledger.get("records") or []
    payload: dict[str, Any] = {
        "kind": "EOD_RECON",
        "day": day,
        "as_of_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offline": offline,
        "ledger": {
            "missing": bool(ledger.get("missing")),
            "record_count": len(records),
            "still_valid_forbidden_overnight": ledger.get(
                "still_valid_forbidden_overnight"
            ),
            "note": ledger.get("note"),
        },
        "candidate_audit": candidate_audit,
        "session": session,
        "event_memory": {
            "score_sample_eligible": bool(session.get("usable_for_retune_sample")),
            "analog_memory_write": True,
            "note": (
                "Outliers (NEWS_DAY/EXPIRY/UNKNOWN) stay in ANALOG_MEMORY; "
                "never rank as typical NORMAL days."
            ),
        },
        "retune_proposal": proposal,
        "promote": False,
        "research_ready_for_programming": False,
        "production_params_written": False,
    }

    out_json = root / "data" / "recon" / f"EOD_RECON_{day}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    continue_path = ""
    if update_continue:
        continue_path = _update_continue(root, day, payload)

    return {
        "day": day,
        "json": str(out_json.relative_to(root)),
        "continue": continue_path,
        "session_kind": session.get("kind"),
        "retune_status": proposal["status"],
        "promote": False,
        "keep_current_strategy": True,
    }
