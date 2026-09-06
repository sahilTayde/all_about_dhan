"""Roll up paper-relevant backtests into one recon artifact. No promote."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agent_rag.paths import load_dotenv, repo_root


SOURCE_JSON = (
    "BACKTEST_HONEST_2026-09-06.json",
    "BACKTEST_SLTP_2026-09-06.json",
    "BACKTEST_CF_FABIO_2026-09-06.json",
    "BACKTEST_CF_MARCO_MAYNE_2026-09-06.json",
    "BACKTEST_CF_MARCI_TORI_2026-09-06.json",
    "BACKTEST_CF_TG_KANE_2026-09-06.json",
    "BACKTEST_CF_UMAR_FOREST_2026-09-06.json",
    "BACKTEST_CF_CARMINE_JADECAP_2026-09-06.json",
    "BACKTEST_CF_USMAN_BRANDO_2026-09-06.json",
    "BACKTEST_CF_ANDREA_OMOR_2026-09-06.json",
    "BACKTEST_CLUB_2026-09-03.json",
)


def _slim_book(book: dict[str, Any]) -> dict[str, Any]:
    oos = book.get("oos") or {}
    return {
        "book_id": book.get("book_id") or book.get("id") or book.get("name"),
        "rating": book.get("rating"),
        "promote": bool(book.get("promote")),
        "validated": book.get("validated"),
        "oos_n": oos.get("n"),
        "oos_win_rate": oos.get("win_rate"),
        "oos_expectancy_pts": oos.get("expectancy_pts"),
        "oos_profit_factor": oos.get("profit_factor"),
        "reason": book.get("reason") or book.get("note"),
        "pnl_unit": book.get("pnl_unit"),
    }


def _load_recon_json(path: Path) -> Optional[dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": "JSON_DECODE", "path": str(path)}
    if not isinstance(raw, dict):
        return {"error": "NOT_OBJECT", "path": str(path)}
    return raw


def _summarize_source(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    books = payload.get("books") or payload.get("results") or []
    slim = [_slim_book(b) for b in books if isinstance(b, dict)]
    ratings: dict[str, int] = {}
    for b in slim:
        r = str(b.get("rating") or "UNKNOWN")
        ratings[r] = ratings.get(r, 0) + 1
    any_promote = any(b.get("promote") for b in slim)
    return {
        "source": name,
        "promote": False if not any_promote else True,
        "research_ready_for_programming": bool(
            payload.get("research_ready_for_programming")
        ),
        "book_count": len(slim),
        "rating_counts": ratings,
        "books_slim": slim[:40],
        "gaps": payload.get("gaps"),
        "as_of_ist": payload.get("as_of_ist"),
        "note": (
            "Proxy / hypothesis backtests only. Not option premium P/L. "
            "KEEP_ALL. No promote on thin samples."
        ),
    }


def run_trading_agents_dry(root: Path) -> dict[str, Any]:
    """Light dry session — does not rewrite trading_agents pipeline."""
    cmd = [
        sys.executable,
        "-m",
        "trading_agents_india",
        "session",
        "--dry-run",
        "--no-persist",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "note": "DATA_INSUFFICIENT — dry session did not run",
        }
    out: dict[str, Any] = {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
    }
    try:
        out["payload"] = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out["stdout_head"] = (proc.stdout or "")[:800]
        out["stderr_head"] = (proc.stderr or "")[:400]
    tickets = (out.get("payload") or {}).get("tickets") or []
    out["ticket_leans"] = [
        {
            "underlying": t.get("underlying"),
            "lean": t.get("lean"),
            "stage": t.get("stage"),
            "session_kind": t.get("session_kind"),
            "risk_veto": t.get("risk_veto"),
        }
        for t in tickets
        if isinstance(t, dict)
    ]
    out["promote"] = False
    return out


def build_paper_agents_report(
    *,
    day: str = "2026-09-06",
    root: Path | None = None,
    run_agents_dry: bool = True,
) -> dict[str, Any]:
    root = root or repo_root()
    recon = root / "data" / "recon"
    sources: list[dict[str, Any]] = []
    missing: list[str] = []
    for name in SOURCE_JSON:
        payload = _load_recon_json(recon / name)
        if payload is None:
            missing.append(name)
            continue
        if payload.get("error"):
            sources.append(payload)
            continue
        sources.append(_summarize_source(name, payload))

    agents = run_trading_agents_dry(root) if run_agents_dry else {"skipped": True}

    promote_any = any(s.get("promote") for s in sources if isinstance(s, dict))
    report: dict[str, Any] = {
        "kind": "BACKTEST_PAPER_AGENTS",
        "day": day,
        "as_of_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "promote": False,
        "keep_current_strategy": True,
        "research_ready_for_programming": False,
        "one_day_pnl_is_not_evidence": True,
        "thin_sample_no_promote": True,
        "sources": sources,
        "missing_sources": missing,
        "trading_agents_india_dry": agents,
        "verdict": {
            "status": "NO_PROMOTE",
            "reasons": [
                "Existing CF / club / SLTP / honest books remain FAIL or WEAK / UNVALIDATED",
                "SCORE_SAMPLE empty (EVENT_MEMORY / news calendar DATA_INSUFFICIENT)",
                "trading_agents_india is paper skeleton only",
                "KEEP_ALL — do not delete STRAT-001–014",
            ],
        },
        "retune_proposal": {
            "kind": "RETUNE_PROPOSAL",
            "status": "BACKTEST_REQUIRED",
            "keep_current_strategy": True,
            "production_params_written": False,
            "backtest_results": None,
        },
    }
    if promote_any:
        report["verdict"]["status"] = "NO_PROMOTE"
        report["verdict"]["reasons"].append(
            "Source JSON claimed promote=true — ignored; desk policy overrides"
        )
        report["promote"] = False
    return report


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        f"# BACKTEST_PAPER_AGENTS — {report.get('day')}",
        "",
        "**Team:** 06_backtesting (+ agent_rag rollup)",
        "**Status:** `HYPOTHESIS` / **UNVALIDATED** / **not a promote**",
        "**Gate:** `keep_current_strategy: true` · **not** `RESEARCH_READY_FOR_PROGRAMMING`",
        "",
        f"Artifact: `data/recon/BACKTEST_PAPER_AGENTS_{report.get('day')}.json`",
        "Command: `python -m agent_rag paper-backtest --day "
        f"{report.get('day')}`",
        "",
        "## Verdict",
        "",
        f"- status: **{report['verdict']['status']}**",
        f"- promote: **{report.get('promote')}**",
        f"- RETUNE_PROPOSAL: **{report['retune_proposal']['status']}**",
        "",
        "Reasons:",
        "",
    ]
    for r in report["verdict"]["reasons"]:
        lines.append(f"- {r}")
    lines += ["", "## Sources rolled up", ""]
    lines.append("| Source | books | ratings | promote |")
    lines.append("|--------|------:|---------|---------|")
    for s in report.get("sources") or []:
        if s.get("error"):
            lines.append(f"| {s.get('path')} | — | ERROR | false |")
            continue
        rc = s.get("rating_counts") or {}
        rc_s = ", ".join(f"{k}:{v}" for k, v in sorted(rc.items()))
        lines.append(
            f"| `{s.get('source')}` | {s.get('book_count')} | {rc_s or '—'} | false |"
        )
    if report.get("missing_sources"):
        lines += ["", "Missing:", ""]
        for m in report["missing_sources"]:
            lines.append(f"- `{m}`")
    agents = report.get("trading_agents_india_dry") or {}
    lines += [
        "",
        "## trading_agents_india dry",
        "",
        f"- ok: `{agents.get('ok')}`",
        f"- ticket leans: `{json.dumps(agents.get('ticket_leans') or [])}`",
        "- LIVE orders: refused (package policy)",
        "",
        "```text",
        "HANDOFF",
        "From: 06 / agent_rag",
        "To:   00 / 09",
        "Accepted: rollup of existing CF/club/sltp/honest JSON + agents dry;",
        "  RETUNE_PROPOSAL BACKTEST_REQUIRED; KEEP_ALL; no promote.",
        "Rejected: promote on thin samples; invent win rates; auto-retune;",
        "  live orders; rewrite trading_agents_india pipeline.",
        "UNKNOWN: SCORE_SAMPLE (empty calendar); option premium path;",
        "  statutory costs.",
        "```",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_paper_backtest(
    *,
    day: str = "2026-09-06",
    root: Path | None = None,
    with_openai: bool = True,
) -> dict[str, Any]:
    load_dotenv()
    root = root or repo_root()
    report = build_paper_agents_report(day=day, root=root, run_agents_dry=True)
    json_path = root / "data" / "recon" / f"BACKTEST_PAPER_AGENTS_{day}.json"
    md_path = root / "teams" / "06_backtesting" / "docs" / f"BACKTEST_PAPER_AGENTS_{day}.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    out: dict[str, Any] = {
        "json": str(json_path.relative_to(root)),
        "md": str(md_path.relative_to(root)),
        "promote": False,
        "verdict": report["verdict"]["status"],
    }
    if with_openai:
        from agent_rag.openai_review import review_paper_backtest

        out["openai_review"] = review_paper_backtest(report, day=day, root=root)
    return out
