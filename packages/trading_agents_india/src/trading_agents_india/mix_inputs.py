"""MIX + optional PhD notes as *inputs to reasons* (never silent deletes).

Cites MIX-DEFAULT-BUY + MIX-TA-* PAPER_WATCH rows. KEEP_ALL STRAT untouched.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PAPER_INPUT_MIXES = (
    "MIX-DEFAULT-BUY",
    "MIX-TA-FLOW-RISK",
    "MIX-TA-EVENT-HOLD",
    "MIX-TA-EXEC-SANITY",
    "MIX-TA-MARKET-HOURS",
    "MIX-LEAN-SPOT-ATM",
    "MIX-IMPULSE-1M",
    "MIX-PCR-EXTREME-HOLD",
    "MIX-003-INDEX-PROXY",
    "MIX-006-INDEX-PROXY",
    "MIX-SELL-CREDIT-PARK",
)

# Short optional note paths (read if present; never invent content).
_PHD_NOTE_RELS = (
    "teams/02_phd_math/docs/CF_USMAN_BRANDO_MATH_NOTES.md",
    "teams/03_phd_market/docs/CF_USMAN_BRANDO_MARKET_NOTES.md",
    "teams/09_review/docs/TRADINGAGENTS_DEEPEN_NOTES_2026-09-06.md",
)


def mix_reason_lines() -> list[str]:
    return [
        f"input_mix:{m} (cited in reasons; not a silent delete; not a promote)"
        for m in PAPER_INPUT_MIXES
    ]


def load_phd_note_snippets(repo_root: Path, *, max_chars: int = 240) -> list[dict[str, Any]]:
    """Best-effort read of PhD/review notes for reason citations."""
    out: list[dict[str, Any]] = []
    for rel in _PHD_NOTE_RELS:
        path = repo_root / rel
        if not path.is_file():
            out.append(
                {
                    "path": rel,
                    "status": "DATA_INSUFFICIENT",
                    "snippet": "",
                }
            )
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            # First non-empty non-heading line after title
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            snippet = ""
            for ln in lines[1:8]:
                if ln.startswith("#"):
                    continue
                snippet = ln[:max_chars]
                break
            out.append({"path": rel, "status": "ok", "snippet": snippet})
        except OSError:
            out.append({"path": rel, "status": "DATA_INSUFFICIENT", "snippet": ""})
    return out


def build_reason_inputs(repo_root: Path) -> dict[str, Any]:
    notes = load_phd_note_snippets(repo_root)
    reasons = list(mix_reason_lines())
    for n in notes:
        if n["status"] == "ok" and n["snippet"]:
            reasons.append(f"phd_note:{n['path']}: {n['snippet'][:160]}")
        else:
            reasons.append(f"phd_note:{n['path']}: DATA_INSUFFICIENT")
    return {
        "mixes_cited": list(PAPER_INPUT_MIXES),
        "phd_notes": notes,
        "reason_lines": reasons,
        "keep_all": "STRAT-001–014 untouched",
        "layer": "HYPOTHESIS",
    }
