"""JSON + MD paper leaderboard. Same path later for paper-live. NO_PROMOTE."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BOARD_JSON = Path("data") / "recon" / "tv_ep_leaderboard.json"
BOARD_MD = Path("data") / "recon" / "tv_ep_leaderboard.md"
DESK_MD = Path("teams") / "06_backtesting" / "docs" / "TV_EP_LEADERBOARD.md"

HONESTY = (
    "**UNVALIDATED.** **NO_PROMOTE.** Not a TradingView Strategy Tester clone. "
    "Not customer `/`. Not `RESEARCH_READY_FOR_PROGRAMMING`. Live orders **refused**. "
    "INDEX points ≠ option P/L. `WATCH` is lab/fixture only."
)

COLS = (
    "| MIX | name | tf | underlying | tape | side (CE/PE) | trades | after-cost note | status | tune hint |"
)
SEP = "|-----|------|----|------------|------|--------------|--------|-----------------|--------|-----------|"


def _cell_line(r: dict[str, Any]) -> str:
    name = (r.get("name") or r.get("title") or "—").replace("|", "/")
    if len(name) > 42:
        name = name[:40] + "…"
    hint = str(r.get("tune_hint") or "—").replace("|", "/")
    if len(hint) > 48:
        hint = hint[:46] + "…"
    note = str(r.get("after_cost_note") or "—").replace("|", "/")
    if len(note) > 40:
        note = note[:38] + "…"
    return (
        f"| `{r.get('mix_id')}` | {name} | {r.get('tf')} | {r.get('underlying')} | "
        f"{r.get('tape')} | {r.get('side') or 'NONE'} | {r.get('trade_count')} | "
        f"{note} | {r.get('status')} | {hint} |"
    )


def _md(report: dict[str, Any], *, desk: bool) -> str:
    counts = report.get("counts") or {}
    mix_rows = report.get("mix_keep_all") or []
    matrix = report.get("ce_pe_matrix") or []
    lines = [
        "# TV-EP paper leaderboard",
        "",
        HONESTY,
        "",
        f"- cells: {counts.get('cells')} · MIX kept: {counts.get('mix_kept') or len(mix_rows)}",
        f"- WATCH: {counts.get('WATCH')} · TESTED_FAIL: {counts.get('TESTED_FAIL')} · "
        f"PARK: {counts.get('PARK')} · DATA_INSUFFICIENT: {counts.get('DATA_INSUFFICIENT')}",
        f"- event calendar: {report.get('event_calendar')}",
        f"- prefer_strike: {report.get('prefer_strike')} (unused unless OPTIDX universe exists)",
        f"- tapes: {', '.join(sorted((report.get('tapes_used') or {}).keys()) or ['fixture/none'])}",
        "",
        "## KEEP_ALL MIX rows (never delete because FAIL / PARK / DI / n=0)",
        "",
        "| MIX | name | side | cells | trades | buy_ce cells | buy_pe cells | status | tune hint |",
        "|-----|------|------|-------|--------|--------------|--------------|--------|-----------|",
    ]
    for m in mix_rows:
        name = (m.get("name") or "—").replace("|", "/")
        if len(name) > 48:
            name = name[:46] + "…"
        hint = str(m.get("tune_hint") or "—").replace("|", "/")
        if len(hint) > 56:
            hint = hint[:54] + "…"
        lines.append(
            f"| `{m.get('mix_id')}` | {name} | {m.get('side')} | {m.get('cells')} | "
            f"{m.get('trades')} | {m.get('buy_ce_cells')} | {m.get('buy_pe_cells')} | "
            f"{m.get('status')} | {hint} |"
        )
    lines += [
        "",
        "## TF × market cells that actually produced BUY_CE and BUY_PE",
        "",
        "Fixture or cache simulation only. Empty matrix ⇒ no ported adapter fired both sides.",
        "",
        "| tf | underlying | tape | BUY_CE | BUY_PE | MIX with CE | MIX with PE |",
        "|----|------------|------|--------|--------|-------------|-------------|",
    ]
    if not matrix:
        lines.append("| — | — | — | no | no | — | — |")
    for slot in matrix:
        ce = "yes" if slot.get("buy_ce") else "no"
        pe = "yes" if slot.get("buy_pe") else "no"
        mix_ce = ",".join(slot.get("mix_ce") or []) or "—"
        mix_pe = ",".join(slot.get("mix_pe") or []) or "—"
        if len(mix_ce) > 60:
            mix_ce = mix_ce[:58] + "…"
        if len(mix_pe) > 60:
            mix_pe = mix_pe[:58] + "…"
        lines.append(
            f"| {slot.get('tf')} | {slot.get('underlying')} | {slot.get('tape')} | "
            f"{ce} | {pe} | {mix_ce} | {mix_pe} |"
        )
    cells = sorted(
        report.get("cells") or [],
        key=lambda r: (
            str(r.get("mix_id") or ""),
            str(r.get("underlying") or ""),
            str(r.get("tf") or ""),
            str(r.get("tape") or ""),
        ),
    )
    listing = [c for c in cells if str(c.get("mix_id") or "").startswith("MIX-TV-EP-")]
    lines += [
        "",
        "## Grid cells (KEEP_ALL; status + reason only)",
        "",
        COLS,
        SEP,
    ]
    cap = None if desk else 120
    shown = listing if cap is None else listing[:cap]
    for r in shown:
        lines.append(_cell_line(r))
    if cap is not None and len(listing) > cap:
        lines.append(f"| … | | | | | | | | | +{len(listing) - cap} more in JSON |")
    lines += [
        "",
        "## Paper-live later",
        "",
        "Attach ticks to **this** JSON (`paper_sessions[]` / `paper_live[]`). Still `NO_PROMOTE`. Do not write customer `/`.
Paper tuner: [`TV_EP_PAPER_TUNE.md`](TV_EP_PAPER_TUNE.md) — `python -m backtest_engine tv-ep-paper-tune`.",
        "",
    ]
    if desk:
        lines += [
            "Recon copies (gitignored): `data/recon/tv_ep_leaderboard.{json,md}`.",
            "Harness: [`TV_EP_BACKTEST_FACTORY.md`](TV_EP_BACKTEST_FACTORY.md).",
            "",
        ]
    return "\n".join(lines) + "\n"


def write_board(report: dict[str, Any], root: Path) -> dict[str, str]:
    json_path = root / BOARD_JSON
    md_path = root / BOARD_MD
    desk_path = root / DESK_MD
    json_path.parent.mkdir(parents=True, exist_ok=True)
    desk_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_md(report, desk=False), encoding="utf-8")
    desk_path.write_text(_md(report, desk=True), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path), "desk": str(desk_path)}
