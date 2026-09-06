"""Markdown report for AUDIT_LATEST.md. No secrets."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docs_auditor.auditor import AuditResult


def render_report(result: "AuditResult") -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [
        "# Docs Auditor — latest",
        "",
        f"**Date (IST):** `{result.as_of_ist}`",
        f"**Result:** **{status}** ({len(result.findings)} finding"
        f"{'' if len(result.findings) == 1 else 's'})",
        "**Cadence:** after any requirement change **and** post-market nightly (`jobs.docs_auditor: daily`)",
        "**CLI:** `python -m docs_auditor` · `python -m desk_intel audit-docs`",
        "**Nightly hook:** end of `python -m desk_intel nightly` / `python -m jobs post-market`",
        "**Agent force:** Cursor rule `.cursor/rules/docs-auditor.mdc` (`alwaysApply: true`) + `.cursor/hooks.json`",
        "**Charter:** [`teams/09_review/docs/DOCS_AUDITOR.md`](../../09_review/docs/DOCS_AUDITOR.md)",
        "",
        "Compare `MASTER_REQUIREMENTS.md`, `AGENT.md`, team `HANDOFF.md` vs code/config "
        "(poll interval, signal states, CAS, retune gate, no live orders). "
        "Does **not** scrape the web. Does **not** print secrets.",
        "",
        "## Findings",
        "",
    ]
    if not result.findings:
        lines.append("_None. Checker ran; do not treat this as `RESEARCH_READY_FOR_PROGRAMMING`._")
        lines.append("")
    else:
        lines += [
            "| Severity | Check | Path | Detail |",
            "|----------|-------|------|--------|",
        ]
        for item in result.findings:
            detail = item.detail.replace("|", "\\|").replace("\n", " ")
            path = item.path.replace("|", "\\|")
            lines.append(
                f"| `{item.severity}` | `{item.check}` | `{path}` | {detail} |"
            )
        lines.append("")
        lines.append(
            "Fix the rows or update the manager sheet, then re-run. "
            "**No requirement merge** while this file is FAIL."
        )
        lines.append("")
    lines += [
        "## Checks run",
        "",
    ]
    for name in result.checks_run:
        lines.append(f"- `{name}`")
    lines += [
        "",
        "## How to re-run",
        "",
        "```bash",
        "python -m docs_auditor",
        "python -m desk_intel audit-docs",
        "python -m jobs post-market --offline   # recon first, auditor last",
        "```",
        "",
        "Exit 0 = pass. Exit 1 = stale/missing/contradicts.",
        "",
        "## Compliance",
        "",
        "Education ≠ advice. Tokens never printed. No live Dhan. No live orders.",
        "",
    ]
    return "\n".join(lines)
