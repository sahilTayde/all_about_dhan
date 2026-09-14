"""JSON + MD paper leaderboard. Same path later for paper-live. NO_PROMOTE."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BOARD_JSON = Path("data") / "recon" / "tv_ep_leaderboard.json"
BOARD_MD = Path("data") / "recon" / "tv_ep_leaderboard.md"


def _md(report: dict[str, Any]) -> str:
    counts = report.get("counts") or {}
    lines = [
        "# TV-EP paper board (NO_PROMOTE)",
        "",
        "**Not** customer `/`. **Not** `RESEARCH_READY_FOR_PROGRAMMING`. Live orders **refused**.",
        "",
        "Honesty: INDEX points ≠ option P/L. `WATCH` is paper-only. Win rates here are **lab/fixture** — not customer truth.",
        "",
        f"- cells: {counts.get('cells')}",
        f"- WATCH: {counts.get('WATCH')} · TESTED_FAIL: {counts.get('TESTED_FAIL')} · "
        f"PARK: {counts.get('PARK')} · DATA_INSUFFICIENT: {counts.get('DATA_INSUFFICIENT')}",
        f"- event calendar: {report.get('event_calendar')}",
        "",
        "| MIX | tape | tf | UL | params | trades | after-cost pts | status |",
        "|-----|------|----|----|--------|--------|----------------|--------|",
    ]
    cells = sorted(
        report.get("cells") or [],
        key=lambda r: (
            0 if r.get("status") == "WATCH" else 1,
            -(
                r.get("after_cost_points")
                if r.get("after_cost_points") is not None
                else (r.get("gross_points") or -1e18)
            ),
        ),
    )
    for r in cells[:80]:
        params = r.get("params") or {}
        ptxt = ",".join(f"{k}={int(v) if float(v).is_integer() else v}" for k, v in params.items()) or "—"
        after = r.get("after_cost_points")
        gross = r.get("gross_points")
        after_s = "—" if after is None else f"{after:.4f}"
        if after is None and gross is not None:
            after_s = f"gross {gross:.4f}"
        lines.append(
            f"| `{r.get('mix_id')}` | {r.get('tape')} | {r.get('tf')} | {r.get('underlying')} | "
            f"{ptxt} | {r.get('trade_count')} | {after_s} | {r.get('status')} |"
        )
    if len(cells) > 80:
        lines.append(f"| … | | | | | | | +{len(cells) - 80} more |")
    lines += [
        "",
        "## Paper-live later",
        "",
        "Attach ticks to **this** JSON (`paper_live[]` later). Still `NO_PROMOTE`. Do not write customer `/`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_board(report: dict[str, Any], root: Path) -> dict[str, str]:
    json_path = root / BOARD_JSON
    md_path = root / BOARD_MD
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_md(report), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}
