"""OpenAI review of paper-agents backtest rollup. Never print API keys."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agent_rag.paths import load_dotenv, repo_root


SYSTEM = """You are a cautious research reviewer for an India index-options
desk (NIFTY/BANKNIFTY/SENSEX CE/PE buy-first). Rules:
- No live orders. No promote on thin samples.
- KEEP_ALL: STRAT-001–014 stay BACKTEST_BOOK.
- RETUNE_PROPOSAL status must stay BACKTEST_REQUIRED for nightly/EOD stubs.
- Do not invent win rates or claim RESEARCH_READY_FOR_PROGRAMMING.
- Prefer HOLD / keep_current_strategy when data is weak.
Respond as JSON with keys: verdict, keep_current_strategy, promote,
risks (array), notes (array of short strings), data_gaps (array).
"""


def _client(model: str):
    key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or "").strip()
    if not key or len(key) < 8:
        return None, "DATA_INSUFFICIENT: OPENAI_API_KEY missing"
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None, "DATA_INSUFFICIENT: openai package not installed"
    return OpenAI(api_key=key), None


def _fallback_notes(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict": "NO_PROMOTE",
        "keep_current_strategy": True,
        "promote": False,
        "risks": [
            "Proxy OHLC books ≠ option premium P/L",
            "SCORE_SAMPLE empty without news calendar",
            "Thin OOS n on several CF books",
        ],
        "notes": [
            "Desk rule fallback (no OpenAI or call failed).",
            f"Rollup sources={len(report.get('sources') or [])}; "
            f"verdict={report.get('verdict', {}).get('status')}.",
            "RETUNE_PROPOSAL remains BACKTEST_REQUIRED. KEEP_ALL.",
        ],
        "data_gaps": [
            "EVENT_MEMORY analogs empty",
            "Statutory costs UNKNOWN",
        ],
        "openai_used": False,
    }


def review_paper_backtest(
    report: dict[str, Any],
    *,
    day: str,
    root: Path | None = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    load_dotenv()
    root = root or repo_root()
    model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    client, err = _client(model)
    review: dict[str, Any]
    if client is None:
        review = _fallback_notes(report)
        if err:
            review["data_gaps"].append(err)
    else:
        slim = {
            "day": report.get("day"),
            "promote": report.get("promote"),
            "verdict": report.get("verdict"),
            "retune_proposal": report.get("retune_proposal"),
            "sources": [
                {
                    "source": s.get("source"),
                    "book_count": s.get("book_count"),
                    "rating_counts": s.get("rating_counts"),
                    "promote": s.get("promote"),
                }
                for s in (report.get("sources") or [])
                if isinstance(s, dict) and not s.get("error")
            ],
            "missing_sources": report.get("missing_sources"),
            "agents_ok": (report.get("trading_agents_india_dry") or {}).get("ok"),
            "ticket_leans": (report.get("trading_agents_india_dry") or {}).get(
                "ticket_leans"
            ),
        }
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=0.2,
                max_tokens=700,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {
                        "role": "user",
                        "content": json.dumps(slim, ensure_ascii=False),
                    },
                ],
            )
            text = (resp.choices[0].message.content or "").strip()
            parsed = json.loads(text)
            raw_verdict = parsed.get("verdict") or "NO_PROMOTE"
            if isinstance(raw_verdict, dict):
                verdict_s = str(
                    raw_verdict.get("status")
                    or raw_verdict.get("verdict")
                    or "NO_PROMOTE"
                )
            else:
                verdict_s = str(raw_verdict)
            review = {
                "verdict": verdict_s,
                "keep_current_strategy": bool(
                    parsed.get("keep_current_strategy", True)
                ),
                "promote": False,  # hard override
                "risks": list(parsed.get("risks") or [])[:12],
                "notes": list(parsed.get("notes") or [])[:20],
                "data_gaps": list(parsed.get("data_gaps") or [])[:12],
                "openai_used": True,
                "model": model,
            }
        except Exception as exc:  # noqa: BLE001
            review = _fallback_notes(report)
            review["data_gaps"].append(
                f"DATA_INSUFFICIENT: OpenAI call failed ({type(exc).__name__})"
            )

    out_path = (
        root
        / "teams"
        / "09_review"
        / "docs"
        / f"PAPER_AGENTS_BACKTEST_OPENAI_REVIEW_{day}.md"
    )
    _append_markdown(out_path, review, day=day)
    return {
        "path": str(out_path.relative_to(root)),
        "openai_used": review.get("openai_used"),
        "verdict": review.get("verdict"),
        "promote": False,
    }


def _append_markdown(path: Path, review: dict[str, Any], *, day: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    verdict = review.get("verdict")
    if isinstance(verdict, dict):
        verdict = verdict.get("status") or verdict.get("verdict") or "NO_PROMOTE"
    block = [
        f"## OpenAI / desk review — {stamp}",
        "",
        f"- day: `{day}`",
        f"- openai_used: `{review.get('openai_used')}`",
        f"- model: `{review.get('model') or 'n/a'}`",
        f"- verdict: **{verdict}**",
        f"- promote: **false** (hard)",
        f"- keep_current_strategy: `{review.get('keep_current_strategy')}`",
        "",
        "### Notes",
        "",
    ]
    for n in review.get("notes") or []:
        block.append(f"- {n}")
    block += ["", "### Risks", ""]
    for n in review.get("risks") or []:
        block.append(f"- {n}")
    block += ["", "### Data gaps", ""]
    for n in review.get("data_gaps") or []:
        block.append(f"- {n}")
    block += [
        "",
        "KEEP_ALL. RETUNE_PROPOSAL stays `BACKTEST_REQUIRED`. No live orders.",
        "",
        "---",
        "",
    ]
    header = (
        f"# PAPER_AGENTS_BACKTEST_OPENAI_REVIEW — {day}\n\n"
        "**Team:** 09_review\n"
        "**Status:** NOTES_ONLY / UNVALIDATED / **not a promote**\n"
        "API keys never printed. Education ≠ advice.\n\n"
        "---\n\n"
    )
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if not existing.startswith("# PAPER_AGENTS"):
            path.write_text(header + existing + "\n".join(block), encoding="utf-8")
        else:
            path.write_text(existing.rstrip() + "\n\n" + "\n".join(block), encoding="utf-8")
    else:
        path.write_text(header + "\n".join(block), encoding="utf-8")
