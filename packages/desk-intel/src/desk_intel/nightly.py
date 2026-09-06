"""POST_MARKET nightly recon + PhD handoff.

Paper daily + pre-prod learning. No live strategy rewrite. No orders.
Never writes production params. Emits RETUNE_PROPOSAL BACKTEST_REQUIRED.

CLI `python -m desk_intel nightly` (and `python -m jobs post-market`) runs
the Docs Auditor after this recon. See desk_intel.docs_audit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from desk_intel.ledger import load_ledger, save_ledger, upsert_records, users_from_ledger
from desk_intel.outcomes import OUTCOME_HELP, outcome_counts, records_from_payloads
from desk_intel.retune_gate import (
    NIGHTLY_RETUNE_STATUS,
    RETUNE_KIND,
    assert_no_production_param_write,
    build_retune_proposal,
    classify_session,
)
from desk_intel.schema import COMPLIANCE_NOTE, LifecycleRecord, MarketSignal, NewsEvent
from desk_intel.store import load_signals_for_day, save_json
from desk_intel.time_ist import now_ist, now_ist_iso

RECON_SCHEMA_VERSION = 1

# Nightly JSON keys (08_testing / 06_backtesting contract). Keep stable; additive OK.
RECON_JSON_KEYS = (
    "schema_version",
    "job",
    "day",
    "as_of_ist",
    "session_close_ist",
    "session_close_note",
    "counts",
    "shadow_pnl_pts_sum",
    "user_pnl_pts_sum",
    "still_valid_remaining",
    "records",
    "param_review_unvalidated",
    "session_kind",
    "session_flags",
    "retune_proposal",
    "production_params_written",
    "cas_calls",
    "compliance",
)

# 03 CAS analyst JSON — same nightly book, separate array. Never auto-retune.
DEFAULT_CAS_CALLS_DIR = "teams/03_phd_market/cas/calls"


def recon_json_path(root: Path, recon_dir: str, day: str) -> Path:
    return root / recon_dir / f"{day}.json"


def phd_handoff_path(root: Path, phd_dir: str, day: str) -> Path:
    return root / phd_dir / f"NIGHTLY_{day}.md"


def cas_calls_path(root: Path, cas_dir: str, day: str) -> Path:
    return root / cas_dir / f"{day}.json"


def load_cas_calls(root: Path, cas_dir: str, day: str) -> list[dict[str, Any]]:
    """Load 03 CAS analyst calls. Missing file → []. Never retunes params."""
    path = cas_calls_path(root, cas_dir or DEFAULT_CAS_CALLS_DIR, day)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        calls = raw.get("calls")
        if isinstance(calls, list):
            return [item for item in calls if isinstance(item, dict)]
    return []


def _param_review(records: list[LifecycleRecord]) -> list[str]:
    hints = [
        "UNVALIDATED — do not retune live. Review only.",
        "If Supertrend/MACD promoted after a 5m impulse: treat as CONFIRMED-late → EXPIRED for new risk (missed-PE postmortem).",
        "Opening-drive veto minutes and event_veto_minutes are yaml knobs — do not treat a one-day recon as proof.",
        "GIFT premium vs cash is a HYPOTHESIS overlay until a public delayed quote is verified.",
        "CAS (Closing Auction Session) cash CTS ends 15:15; equity derivatives 15:40 — see teams/03_phd_market/cas/RESEARCH.md. Do not hardcode forever.",
        "cas_calls[] are UNVALIDATED pattern notes. BACKTEST_REQUIRED. Never auto-retune.",
    ]
    late = sorted({item for rec in records for item in rec.lagging_late})
    hints.extend(late)
    return hints


def render_phd_markdown(
    *,
    day: str,
    session_close_ist: str,
    session_close_note: str,
    counts: dict[str, Any],
    records: list[LifecycleRecord],
    param_review: list[str],
    session_kind: str = "NORMAL",
    session_flags: Optional[list[str]] = None,
    retune_proposal: Optional[dict[str, Any]] = None,
    cas_calls: Optional[list[dict[str, Any]]] = None,
) -> str:
    flags = session_flags or [session_kind]
    proposal = retune_proposal or {}
    lines = [
        f"# Nightly recon {day}",
        "",
        "**Status:** `HYPOTHESIS` / `UNVALIDATED`. Paper + shadow P/L only. **Education ≠ advice.** No live orders.",
        "",
        f"**Session close:** `{session_close_ist}` — {session_close_note or 'VERIFY FROM NSE/BSE circular. Do not hardcode 15:30 vs 15:40.'}",
        "",
        "Handed to **02_phd_math** as **REVIEW**, not auto-apply. Do not retune live from this file.",
        "",
        "## Session tag",
        "",
        f"- `session_kind`: **`{session_kind}`**",
        f"- flags: {', '.join(f'`{f}`' for f in flags) or '—'}",
        "- Event days (`NEWS_DAY` / `EXPIRY`) are **not** a retune sample. Default: **keep current strategy**.",
        "",
        "## RETUNE_PROPOSAL",
        "",
        f"- kind: `{proposal.get('kind') or RETUNE_KIND}`",
        f"- status: **`{proposal.get('status') or NIGHTLY_RETUNE_STATUS}`** (nightly never writes production params)",
        f"- keep_current_strategy: `{proposal.get('keep_current_strategy', True)}`",
        f"- production_params_written: `{proposal.get('production_params_written', False)}`",
        "- Handoff: **REVIEW** (02_phd_math). Backtest owner: **06_backtesting**.",
        "- Promote only after OOS + `NORMAL` days on expectancy / PF / DD vs current, or a documented glitch fix. **No invented metrics.**",
        f"- backtest_results: `{proposal.get('backtest_results')}`",
        "",
        "## Counts",
        "",
        f"- User taken: **{counts.get('user_taken', 0)}**",
        f"- User skipped (shadow-papered): **{counts.get('user_skipped', 0)}**",
        f"- Hit target (`ACHIEVED`): **{counts.get('hit_target', 0)}**",
        f"- Missed SL (`STOPPED`): **{counts.get('missed_sl', 0)}**",
        f"- Invalidated: **{counts.get('invalidated', 0)}**",
        f"- Still valid after recon (must be 0 overnight): **{counts.get('still_valid', 0)}**",
        f"- Shadow P/L pts (sum): **{counts.get('shadow_pnl_pts_sum', 0)}**",
        f"- User reported P/L pts (sum): **{counts.get('user_pnl_pts_sum', 0)}**",
        "",
        "## Outcome enum",
        "",
    ]
    for key, help_text in OUTCOME_HELP.items():
        lines.append(f"- `{key}` — {help_text}")
    lines += [
        "",
        "## Trades / shadows",
        "",
    ]
    if not records:
        lines.append("_No MARKET_SIGNAL files for this day — DATA_INSUFFICIENT. Ran schema-only recon._")
        lines.append("")
    for rec in records:
        user = "TOOK" if rec.user.took_trade else "SKIPPED"
        lots = rec.user.lots if rec.user.lots is not None else "—"
        spot = rec.user.spot if rec.user.spot is not None else "—"
        upnl = rec.user.reported_pnl if rec.user.reported_pnl is not None else "—"
        spnl = rec.shadow.pnl_pts if rec.shadow.pnl_pts is not None else "—"
        lines.append(
            f"- `{rec.signal_id}` {rec.underlying} `{rec.lean}` stage=`{rec.stage}` "
            f"outcome=`{rec.outcome}` still_valid={rec.still_valid} user={user} "
            f"lots={lots} spot={spot} user_pnl={upnl} shadow_pnl={spnl}"
        )
        for reason in rec.reasons:
            lines.append(f"  - {reason}")
        for late in rec.lagging_late:
            lines.append(f"  - lagging (UNVALIDATED): {late}")
    lines += [
        "",
        "## Suggested param review (UNVALIDATED)",
        "",
    ]
    for hint in param_review:
        lines.append(f"- {hint}")
    lines += [
        "",
        "## CAS calls (UNVALIDATED)",
        "",
        "Official **CAS** = Closing Auction Session. Same recon book, separate array. "
        "**BACKTEST_REQUIRED** — do not auto-retune from these rows.",
        "",
    ]
    if not cas_calls:
        lines.append("_No `cas_calls[]` for this day — DATA_INSUFFICIENT or file missing._")
        lines.append("")
    else:
        for call in cas_calls:
            und = call.get("underlying") or "—"
            bias = call.get("bias") or "SIDEWAYS"
            conf = call.get("confidence")
            mech = call.get("mechanism") or "CLOSING_AUCTION_SESSION"
            window = call.get("window") or "—"
            realized = call.get("realized_bias")
            notes = call.get("notes") or ""
            lines.append(
                f"- `{und}` bias=`{bias}` conf={conf} mechanism=`{mech}` "
                f"window=`{window}` realized=`{realized}` retune=`BACKTEST_REQUIRED`"
            )
            if notes:
                lines.append(f"  - {notes}")
        lines.append("")
    lines += [
        "",
        "## Pointers",
        "",
        "- Paper daily + pre-prod: `packages/desk-intel` ledger + `data/recon/`.",
        "- Do **not** rewrite live strategy code from this file. Gate: `teams/06_backtesting/docs/RETUNE_GATE.md`.",
        "- 02 REVIEW note: `teams/02_phd_math/docs/handoffs/README.md`.",
        "- 04_quant staging: `teams/04_quant/docs/SIGNAL_STAGING.md`.",
        "- 06_backtesting: consume nightly JSON when an engine exists; costs/slippage still required. No one-day promote.",
        "- CAS analyst: `teams/03_phd_market/cas/` — `cas_calls[]` only; never production params.",
        "",
        f"_{COMPLIANCE_NOTE}_",
        "",
    ]
    return "\n".join(lines) + "\n"


def run_nightly(
    cfg: Any,
    *,
    day: Optional[str] = None,
    persist: bool = True,
    fixture_signals: Optional[list[MarketSignal]] = None,
    marks: Optional[dict[str, float]] = None,
    session_expired: bool = True,
    events: Optional[list[NewsEvent]] = None,
) -> dict[str, Any]:
    root = cfg.repo_root
    settings = cfg.desk_intel
    day = day or now_ist().date().isoformat()
    signals = load_signals_for_day(root, settings.signals_dir, day)
    if not signals and fixture_signals:
        signals = fixture_signals

    ledger = load_ledger(root, settings.ledger_dir, day)
    users = users_from_ledger(ledger)
    mark_map = marks or {}
    records = records_from_payloads(
        signals,
        users=users,
        marks=mark_map,
        session_expired=session_expired,
    )
    counts = outcome_counts(records)
    still = sum(1 for r in records if r.still_valid)
    param_review = _param_review(records)
    session = classify_session(
        day=day, signals=signals, events=events, records=records
    )
    proposal = build_retune_proposal(
        session=session, candidate_notes=param_review
    )
    proposal_payload = proposal.to_dict()
    job = cfg.jobs.post_market
    cas_dir = getattr(settings, "cas_calls_dir", None) or DEFAULT_CAS_CALLS_DIR
    cas_calls = load_cas_calls(root, cas_dir, day)

    payload = {
        "schema_version": RECON_SCHEMA_VERSION,
        "job": "POST_MARKET",
        "day": day,
        "as_of_ist": now_ist_iso(),
        "session_close_ist": job.session_close_ist,
        "session_close_note": job.session_close_note,
        "after_ist": job.after_ist,
        "counts": counts,
        "shadow_pnl_pts_sum": counts.get("shadow_pnl_pts_sum"),
        "user_pnl_pts_sum": counts.get("user_pnl_pts_sum"),
        "still_valid_remaining": still,
        "records": [r.to_dict() for r in records],
        "param_review_unvalidated": param_review,
        "session_kind": session.kind,
        "session_flags": list(session.flags),
        "retune_proposal": proposal_payload,
        "production_params_written": False,
        "cas_calls": cas_calls,
        "outcome_help": OUTCOME_HELP,
        "compliance": COMPLIANCE_NOTE,
        "execution": "refused",
    }

    written_json = None
    written_md = None
    written_ledger = None
    if persist:
        ledger = upsert_records(ledger, records)
        written_ledger = str(save_ledger(root, settings.ledger_dir, ledger, day))
        written_json = str(save_json(recon_json_path(root, settings.recon_dir, day), payload))
        md = render_phd_markdown(
            day=day,
            session_close_ist=job.session_close_ist,
            session_close_note=job.session_close_note,
            counts=counts,
            records=records,
            param_review=param_review,
            session_kind=session.kind,
            session_flags=list(session.flags),
            retune_proposal=proposal_payload,
            cas_calls=cas_calls,
        )
        md_path = phd_handoff_path(root, settings.phd_handoff_dir, day)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md, encoding="utf-8")
        written_md = str(md_path)
        assert_no_production_param_write(
            (written_json, written_md, written_ledger)
        )

    return {
        "job": "POST_MARKET",
        "day": day,
        "signal_count": len(signals),
        "still_valid_remaining": still,
        "counts": counts,
        "session_kind": session.kind,
        "retune_proposal": proposal_payload,
        "production_params_written": False,
        "recon_json": written_json,
        "phd_handoff": written_md,
        "ledger": written_ledger,
        "compliance": COMPLIANCE_NOTE,
    }
