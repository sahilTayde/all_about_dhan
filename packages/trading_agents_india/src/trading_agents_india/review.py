"""Frontier-model review helper for the TradingAgents adoption plan."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Optional

from trading_agents_india.llm import LlmClient

LOCAL_REVIEW = {
    "verdict": "ADOPT_SKELETON_OK_WITH_GAPS",
    "openai_used": False,
    "layer": "HYPOTHESIS",
    "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
    "accept": [
        "Additive packages/trading_agents_india does not rewrite monorepo or KEEP_ALL catalog",
        "News/MACRO_EVENT mapped to ticket HOLD aligned with EVENT_MEMORY / SIGNAL_FUSION",
        "Separate SQLite KB preserves transcripts.sqlite",
        "Structured CE/PE/HOLD + risk veto matches paper-only mandate",
        "TradingAgents roles mapped onto 00/04/05/06 without inventing STRAT-015+",
    ],
    "reject_or_watch": [
        "Do not import US equity fundamentals / StockTwits as India SOURCE_FACT",
        "Do not claim CONFIRMED/IN-PROGRESS from agent loop alone (v0 caps at EARLY)",
        "Do not treat Docs Auditor PASS or this review as product gate",
        "LangGraph full port deferred — sequential pipeline is enough for paper dry-run",
    ],
    "data_insufficient": [
        "OPENAI_API_KEY not present in workspace .env at adopt time — live frontier call skipped",
        "EVENT_MEMORY analogs empty",
        "Live Dhan chain optional; fixtures used for dry-run",
        "India sentiment feed not wired",
    ],
    "must_keep": [
        "KEEP_ALL STRAT-001–014",
        "No live Dhan orders / no /alerts/orders",
        "Layers SOURCE_FACT / VALIDATION / HYPOTHESIS",
        "Apache-2.0 citation for TradingAgents",
    ],
}


def run_frontier_review(*, adopt_text: str, llm: LlmClient) -> dict[str, Any]:
    if not llm.enabled:
        out = dict(LOCAL_REVIEW)
        out["reviewer"] = "local_rule_fallback"
        out["note"] = (
            "Frontier OpenAI review unavailable; recorded careful local verification against "
            "BOSS_AGENT / EVENT_MEMORY / KEEP_ALL constraints."
        )
        return out

    system = (
        "You are a red-team frontier reviewer for an Indian index-options research desk. "
        "Education ≠ advice. No live orders. KEEP_ALL STRAT-001–014. "
        "Return JSON with keys: verdict, accept[], reject_or_watch[], data_insufficient[], "
        "must_keep[], notes. Be strict; do not invent win rates or declare RESEARCH_READY."
    )
    user = (
        "Review this adoption plan for TradingAgents → all_about_dhan:\n\n"
        + adopt_text[:12000]
    )
    parsed, gaps = llm.complete_json(system=system, user=user, max_tokens=1200)
    if not parsed:
        out = dict(LOCAL_REVIEW)
        out["openai_used"] = False
        out["data_insufficient"] = list(LOCAL_REVIEW["data_insufficient"]) + gaps
        out["reviewer"] = "local_rule_fallback_after_llm_error"
        return out

    return {
        "verdict": parsed.get("verdict", "REVIEW"),
        "openai_used": True,
        "reviewer": f"openai:{llm.model}",
        "layer": "HYPOTHESIS",
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "accept": list(parsed.get("accept") or []),
        "reject_or_watch": list(parsed.get("reject_or_watch") or []),
        "data_insufficient": list(parsed.get("data_insufficient") or []) + gaps,
        "must_keep": list(parsed.get("must_keep") or LOCAL_REVIEW["must_keep"]),
        "notes": parsed.get("notes", ""),
    }


def build_review_markdown(review: dict[str, Any], *, openai_key_present: bool) -> str:
    today = date.today().isoformat()
    lines = [
        f"# TRADINGAGENTS adoption review — {today}",
        "",
        "**Team:** 09_review",
        f"**Layer:** `{review.get('layer', 'HYPOTHESIS')}`",
        f"**Gate:** **{review.get('gate', 'not RESEARCH_READY_FOR_PROGRAMMING')}**",
        f"**Verdict:** `{review.get('verdict')}`",
        f"**Reviewer:** {review.get('reviewer', 'unknown')}",
        f"**OpenAI used:** `{review.get('openai_used')}` (key_present={openai_key_present})",
        "",
        "EXTERNAL reference: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0).",
        "Plan: [`ADOPT_TRADINGAGENTS.md`](../../00_orchestrator/docs/ADOPT_TRADINGAGENTS.md).",
        "",
        "This is **NOTES_ONLY** / design verification — **not** a five-pass product pass.",
        "",
        "## Accept",
        "",
    ]
    for item in review.get("accept") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Reject / watch", ""])
    for item in review.get("reject_or_watch") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## DATA_INSUFFICIENT / UNKNOWN", ""])
    for item in review.get("data_insufficient") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Must keep", ""])
    for item in review.get("must_keep") or []:
        lines.append(f"- {item}")
    if review.get("notes"):
        lines.extend(["", "## Notes", "", str(review["notes"])])
    if review.get("note"):
        lines.extend(["", "## Fallback note", "", str(review["note"])])
    lines.extend(
        [
            "",
            "## Raw JSON",
            "",
            "```json",
            json.dumps(review, indent=2, ensure_ascii=False),
            "```",
            "",
        ]
    )
    return "\n".join(lines) + "\n"
