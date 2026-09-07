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


def _load_paper_ledger_jsonl(root: Path, day: str) -> dict[str, Any]:
    """Primary paper agents ledger: data/recon/paper_ledger/{day}.jsonl."""
    path = root / "data" / "recon" / "paper_ledger" / f"{day}.jsonl"
    if not path.is_file():
        return {
            "day": day,
            "note": "DATA_INSUFFICIENT — no paper_ledger jsonl for day",
            "users": {},
            "records": [],
            "missing": True,
            "source": "paper_ledger_jsonl",
            "path": str(path.relative_to(root)) if root in path.parents else str(path),
        }
    signal_count = 0
    lean_counts: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()
    reason_hits: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                et = str(row.get("event_type") or "")
                if et == "SIGNAL":
                    signal_count += 1
                    lean = str(row.get("lean") or row.get("side") or "?")
                    lean_counts[lean] += 1
                    stage = str(row.get("stage") or "?")
                    stage_counts[stage] += 1
                    for r in (row.get("reasons") or row.get("vetoes") or [])[:4]:
                        text_r = str(r)
                        if text_r.startswith(("BIG_NEWS", "NEWS_DAY", "cited_news", "EXPIRY", "MIX-CLOCK")):
                            reason_hits[text_r[:120]] += 1
                    # Keep a thin sample only — do not materialize 47MB into memory.
                    if len(records) < 32:
                        records.append(
                            {
                                "event_type": "SIGNAL",
                                "underlying": row.get("underlying"),
                                "lean": lean,
                                "stage": stage,
                                "session_kind": row.get("session_kind"),
                                "risk_veto": row.get("risk_veto"),
                            }
                        )
    except OSError:
        return {
            "day": day,
            "error": "OS_ERROR",
            "records": [],
            "missing": True,
            "source": "paper_ledger_jsonl",
        }
    return {
        "day": day,
        "missing": False,
        "source": "paper_ledger_jsonl",
        "path": str(path.relative_to(root)),
        "users": {},
        "records": records,
        "signal_count": signal_count,
        "lean_counts": dict(sorted(lean_counts.items())),
        "stage_counts": dict(sorted(stage_counts.items())),
        "top_reason_hits": dict(reason_hits.most_common(8)),
        "still_valid_forbidden_overnight": True,
        "note": (
            f"PAPER ledger jsonl: signal_count={signal_count}. "
            "Sample records only; not a promote. Orders refused."
        ),
    }


def _load_desk_intel_ledger(root: Path, day: str) -> dict[str, Any]:
    path = root / "data" / "desk_intel" / "ledger" / day / "ledger.json"
    if not path.is_file():
        return {
            "day": day,
            "note": "DATA_INSUFFICIENT — no desk_intel ledger.json for day",
            "users": {},
            "records": [],
            "missing": True,
            "source": "desk_intel_ledger",
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "day": day,
            "error": "JSON_DECODE",
            "records": [],
            "missing": True,
            "source": "desk_intel_ledger",
        }
    if not isinstance(raw, dict):
        return {
            "day": day,
            "error": "NOT_OBJECT",
            "records": [],
            "missing": True,
            "source": "desk_intel_ledger",
        }
    raw["missing"] = False
    raw.setdefault("source", "desk_intel_ledger")
    return raw


def _load_ledger(root: Path, day: str) -> dict[str, Any]:
    """Prefer paper_ledger jsonl (agents truth); desk_intel ledger.json secondary."""
    paper = _load_paper_ledger_jsonl(root, day)
    if not paper.get("missing"):
        return paper
    desk = _load_desk_intel_ledger(root, day)
    if not desk.get("missing"):
        return desk
    return {
        "day": day,
        "note": "DATA_INSUFFICIENT — no paper_ledger jsonl or desk_intel ledger for day",
        "users": {},
        "records": [],
        "missing": True,
        "source": "none",
    }


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
    outcomes: Counter[str] = Counter()
    di_reasons: Counter[str] = Counter()
    bound_true = 0
    bound_false = 0
    by_candidate_outcome: Counter[str] = Counter()
    candidate_ids: set[str] = set()
    observation_count = 0
    marks_available = False
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("event_type") != "CANDIDATE_OBSERVATION":
                    continue
                observation_count += 1
                cid = str(row.get("candidate_id") or "?")
                candidate_ids.add(cid)
                outcome = str(row.get("outcome") or "?")
                outcomes[outcome] += 1
                by_candidate_outcome[f"{cid}:{outcome}"] += 1
                prov = row.get("provenance") or {}
                avail = prov.get("candidate_evaluator_available")
                if avail is True:
                    bound_true += 1
                elif avail is False:
                    bound_false += 1
                if outcome == "DATA_INSUFFICIENT":
                    gaps = row.get("data_gaps") or []
                    if gaps:
                        # Single aggregated reason preferred — take first gap only.
                        di_reasons[str(gaps[0])[:160]] += 1
                    else:
                        di_reasons["(no gap text)"] += 1
                if outcome in {"ACHIEVED", "STOPPED", "INVALIDATED", "LOST"}:
                    marks_available = True
    except OSError:
        return {
            "missing": True,
            "observation_count": 0,
            "note": "DATA_INSUFFICIENT — candidate audit mirror unreadable",
        }
    return {
        "missing": False,
        "observation_count": observation_count,
        "candidate_ids": sorted(candidate_ids),
        "outcome_counts": dict(sorted(outcomes.items())),
        "evaluator_available_true": bound_true,
        "evaluator_available_false": bound_false,
        "top_di_reasons": dict(di_reasons.most_common(8)),
        "top_candidate_outcomes": dict(by_candidate_outcome.most_common(16)),
        "marks_available": marks_available,
        "pnl_available": False,
        "note": (
            "PAPER observations only; marks and P/L are absent unless an "
            "authoritative mark adapter appends them."
        ),
    }


def _scan_signal_learning(root: Path, day: str) -> dict[str, Any]:
    """Extract veto / news / LLM observations from SIGNAL rows (no win rates)."""
    path = root / "data" / "recon" / "paper_ledger" / f"{day}.jsonl"
    empty = {
        "missing": True,
        "signal_count": 0,
        "veto_freq": {},
        "news_severity_hits": {},
        "llm_error_hits": {},
        "lean_counts": {},
        "stage_counts": {},
    }
    if not path.is_file():
        return empty
    signal_count = 0
    veto_freq: Counter[str] = Counter()
    news_hits: Counter[str] = Counter()
    llm_hits: Counter[str] = Counter()
    lean_counts: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("event_type") != "SIGNAL":
                    continue
                signal_count += 1
                lean_counts[str(row.get("lean") or "?")] += 1
                stage_counts[str(row.get("stage") or "?")] += 1
                texts = []
                for key in ("vetoes", "reasons", "top_veto_reasons", "data_gaps"):
                    for item in row.get(key) or []:
                        texts.append(str(item))
                for text in texts:
                    u = text.upper()
                    if "BIG_NEWS" in u:
                        news_hits["BIG_NEWS"] += 1
                    elif "NEWS_DAY" in u:
                        news_hits["NEWS_DAY"] += 1
                    elif "PREMARKET" in u:
                        news_hits["PREMARKET"] += 1
                    if any(
                        k in u
                        for k in (
                            "RATELIMIT",
                            "RATE-LIMIT",
                            "RATE_LIMIT",
                            "OPENAI CALL FAILED",
                            "CONNECTION COOLDOWN",
                            "API CONNECTION",
                        )
                    ):
                        # Class-ish token only — never log secrets / full bodies.
                        label = "LLM_ERROR"
                        for token in (
                            "RateLimitError",
                            "RateLimitCooldown",
                            "APIConnectionCooldown",
                            "OpenAI",
                        ):
                            if token.upper().replace(" ", "") in u.replace(" ", "").replace("-", ""):
                                label = token
                                break
                        if "RATE" in u and "LIMIT" in u:
                            label = "RateLimit"
                        elif "CONNECTION" in u and "COOLDOWN" in u:
                            label = "APIConnectionCooldown"
                        llm_hits[label] += 1
                    if row.get("risk_veto") or str(row.get("stage") or "").upper() == "VETOED":
                        veto_freq[text[:120]] += 1
    except OSError:
        return empty
    return {
        "missing": False,
        "signal_count": signal_count,
        "veto_freq": dict(veto_freq.most_common(12)),
        "news_severity_hits": dict(sorted(news_hits.items())),
        "llm_error_hits": dict(sorted(llm_hits.items())),
        "lean_counts": dict(sorted(lean_counts.items())),
        "stage_counts": dict(sorted(stage_counts.items())),
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
    else:
        sc = ledger.get("signal_count")
        if sc is not None:
            reasons.append(
                f"paper_ledger jsonl signal_count={sc} source={ledger.get('source')}"
            )
        leans = ledger.get("lean_counts") or {}
        if leans:
            reasons.append(f"lean_counts={leans}")
    records = ledger.get("records") or []
    if records and ledger.get("signal_count") is None:
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


def build_retune_proposal(
    session: dict[str, Any],
    *,
    observations: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Always BACKTEST_REQUIRED. Surfaces dig observations; never tunes params."""
    obs = observations or {}
    has_dig = bool(
        obs.get("signal_count")
        or obs.get("candidate_observation_count")
        or (obs.get("veto_freq") or obs.get("top_di_reasons"))
    )
    # Honest: we ran and extracted observations, but did not tune production params.
    tune_status = "RAN_NO_TUNE" if has_dig else "RAN_EMPTY_LEDGER"
    done_when = [
        "06 OOS + NORMAL backtest fills expectancy / profit_factor / max_drawdown",
        "session_usable_for_retune_sample=true (NORMAL ∧ ¬CIRCUIT ∧ ¬GAP)",
        "human REVIEW accepts candidate; production_params_written still false until promote gate",
        "NO_PROMOTE until RESEARCH_READY_FOR_PROGRAMMING and 09 five-pass",
    ]
    return {
        "kind": "RETUNE_PROPOSAL",
        "status": "BACKTEST_REQUIRED",
        "tune_status": tune_status,
        "tuned": False,
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
        "observations": obs,
        "done_when": done_when,
        "candidate_notes": [
            "EOD extracted observations from paper_ledger / candidates — not a tune.",
            f"tune_status={tune_status} (RAN_NO_TUNE ≠ silent success).",
            "Paper ledger P/L is not promote evidence.",
            f"score_track={session.get('score_track')}",
        ],
        "note": (
            "Default: keep current strategy. Dig ran; params not written. "
            "06 must backtest OOS + NORMAL before any promote. Do not invent metrics."
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
            f"/ tune_status=`{payload['retune_proposal'].get('tune_status', 'RAN_NO_TUNE')}` "
            "(no auto-retune; `keep_current_strategy: true`; "
            "`production_params_written: false`)",
            f"- recon: `data/recon/EOD_RECON_{day}.json`",
            f"- retune artifact: `data/recon/RETUNE_PROPOSAL_{day}.json`",
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
    signal_learn = _scan_signal_learning(root, day)
    session = _classify_session(
        day=day, ledger=ledger, nightly=nightly, offline=offline
    )
    observations = {
        "day": day,
        "signal_count": signal_learn.get("signal_count")
        or ledger.get("signal_count")
        or 0,
        "lean_counts": signal_learn.get("lean_counts") or ledger.get("lean_counts") or {},
        "stage_counts": signal_learn.get("stage_counts")
        or ledger.get("stage_counts")
        or {},
        "veto_freq": signal_learn.get("veto_freq") or {},
        "news_severity_hits": signal_learn.get("news_severity_hits") or {},
        "llm_error_hits": signal_learn.get("llm_error_hits") or {},
        "candidate_observation_count": candidate_audit.get("observation_count") or 0,
        "candidate_outcome_counts": candidate_audit.get("outcome_counts") or {},
        "evaluator_available_true": candidate_audit.get("evaluator_available_true"),
        "evaluator_available_false": candidate_audit.get("evaluator_available_false"),
        "top_di_reasons": candidate_audit.get("top_di_reasons") or {},
        "note": (
            "Observations only — not expectancy/PF/DD. "
            "tuned=false; production_params_written=false."
        ),
    }
    proposal = build_retune_proposal(session, observations=observations)

    records = ledger.get("records") or []
    payload: dict[str, Any] = {
        "kind": "EOD_RECON",
        "day": day,
        "as_of_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offline": offline,
        "ledger": {
            "missing": bool(ledger.get("missing")),
            "source": ledger.get("source"),
            "path": ledger.get("path"),
            "record_count": len(records),
            "signal_count": ledger.get("signal_count"),
            "lean_counts": ledger.get("lean_counts"),
            "stage_counts": ledger.get("stage_counts"),
            "top_reason_hits": ledger.get("top_reason_hits"),
            "still_valid_forbidden_overnight": ledger.get(
                "still_valid_forbidden_overnight"
            ),
            "note": ledger.get("note"),
        },
        "candidate_audit": candidate_audit,
        "learning_observations": observations,
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
        "tune_status": proposal.get("tune_status"),
        "tuned": False,
        "promote": False,
        "research_ready_for_programming": False,
        "production_params_written": False,
    }

    out_dir = root / "data" / "recon"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"EOD_RECON_{day}.json"
    out_json.write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    # Standalone RETUNE_PROPOSAL artifact for founder dig review.
    retune_path = out_dir / f"RETUNE_PROPOSAL_{day}.json"
    retune_path.write_text(
        json.dumps(proposal, indent=2, default=str) + "\n", encoding="utf-8"
    )
    continue_path = ""
    if update_continue:
        continue_path = _update_continue(root, day, payload)

    return {
        "day": day,
        "json": str(out_json.relative_to(root)),
        "retune_proposal_json": str(retune_path.relative_to(root)),
        "continue": continue_path,
        "session_kind": session.get("kind"),
        "retune_status": proposal["status"],
        "tune_status": proposal.get("tune_status"),
        "tuned": False,
        "promote": False,
        "keep_current_strategy": True,
        "production_params_written": False,
    }
