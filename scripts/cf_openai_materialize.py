#!/usr/bin/env python3
"""Materialize CF OpenAI suggests → BIND refresh notes + India MIX stubs + skips.

Reads data/recon/CF_OPENAI_*_BIND_SUGGEST_2026-09-07.json
Writes:
  - BIND rev appendix (or new BIND) under teams/01_research/docs/chart_fanatics/
  - MIX candidate stubs MIX-CF-*-IN-* under teams/04_quant/docs/candidates/
  - data/recon/CF_OVERNIGHT_SKIPS_2026-09-07.md
  - data/recon/CF_OVERNIGHT_C_SUMMARY_2026-09-07.json

Does NOT rewrite okala_in_proxy. Sibling runner stub: cf_india_runner.py (optional --write-runner).
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CF = ROOT / "teams/01_research/docs/chart_fanatics"
CAND = ROOT / "teams/04_quant/docs/candidates"
RECON = ROOT / "data/recon"
DATE = "2026-09-07"

# Mirror batch metadata
VIDEOS = [
    {"id": "tvERE-Beu2U", "guest": "Fabio Valentini", "slug": "FABIO", "mix_prefix": "MIX-CF-FABIO"},
    {"id": "DAnXM7C16h0", "guest": "Marco", "slug": "MARCO", "mix_prefix": "MIX-CF-MARCO"},
    {"id": "coBMd1vk2Lo", "guest": "Trader Mayne", "slug": "MAYNE", "mix_prefix": "MIX-CF-MAYNE"},
    {"id": "AVVM-FyewLg", "guest": "Marci Silfrain", "slug": "MARCI", "mix_prefix": "MIX-CF-MARCI"},
    {"id": "VTEQ2fhGLqE", "guest": "Tori Trades", "slug": "TORI", "mix_prefix": "MIX-CF-TORI"},
    {"id": "ADnslyKOwFE", "guest": "TG Capital", "slug": "TG", "mix_prefix": "MIX-CF-TG"},
    {"id": "HNuRp9Z1bMs", "guest": "Trader Kane", "slug": "KANE", "mix_prefix": "MIX-CF-KANE"},
    {"id": "IUo5AwmsE9A", "guest": "Umar Ashraf", "slug": "UMAR", "mix_prefix": "MIX-CF-UMAR"},
    {"id": "q_MdVlZ1SH4", "guest": "Forest Knight", "slug": "FOREST", "mix_prefix": "MIX-CF-FOREST"},
    {"id": "UhkRRqO1gQM", "guest": "Carmine Rosato", "slug": "CARMINE", "mix_prefix": "MIX-CF-CARMINE"},
    {"id": "8OX-mcSHWhg", "guest": "Jadecap", "slug": "JADECAP", "mix_prefix": "MIX-CF-JADECAP"},
    {"id": "6Bdv-_YUQ0s", "guest": "Usman Ashraf", "slug": "USMAN", "mix_prefix": "MIX-CF-USMAN"},
    {"id": "yLuH8YZXORQ", "guest": "Brando / Leaf", "slug": "BRANDO", "mix_prefix": "MIX-CF-BRANDO"},
    {"id": "TvoQr6ObjnU", "guest": "Andrea Cimi", "slug": "ANDREA", "mix_prefix": "MIX-CF-ANDREA"},
    {"id": "IB-fyWI5j8w", "guest": "Omor / NBB", "slug": "OMOR", "mix_prefix": "MIX-CF-OMOR"},
    {"id": "hvyf6frvCcA", "guest": "Trader Yush", "slug": "YUSH", "mix_prefix": "MIX-CF-YUSH"},
    {"id": "T_djSNBmV00", "guest": "Marco (DaVinci return)", "slug": "MARCO-DAV", "mix_prefix": "MIX-CF-MARCO-DAV"},
]


def jdump(x: Any) -> str:
    return json.dumps(x, indent=2, ensure_ascii=False)


def as_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    return jdump(x)


def load_suggest(slug: str) -> dict | None:
    path = RECON / f"CF_OPENAI_{slug}_BIND_SUGGEST_{DATE}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_mix_id(raw: str, fallback_prefix: str) -> str:
    s = (raw or "").strip().upper().replace(" ", "-")
    s = re.sub(r"[^A-Z0-9\-]", "", s)
    if not s.startswith("MIX-CF-"):
        s = f"{fallback_prefix}-{s}" if s else f"{fallback_prefix}-IN-CORE"
    # forbid STRAT-
    if "STRAT-" in s:
        s = s.replace("STRAT-", "MIX-CF-")
    return s[:64]


def write_india_candidate(
    mix_id: str,
    *,
    guest: str,
    video_id: str,
    slug: str,
    teacher_hint: str,
    one_line: str,
    of_required: bool,
    decision: str,
    openai_rel: str,
) -> Path:
    status = "DATA_INSUFFICIENT" if decision == "SKIP" or of_required else "BACKTEST_BOOK"
    if decision == "PARTIAL":
        status = "BACKTEST_BOOK"
    body = f"""# {mix_id} — India adaptation ({guest})

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `{status}`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `{video_id}` ({guest})  
**Teacher book:** {teacher_hint or "(see BIND)"}  
**Bind:** [`../../01_research/docs/chart_fanatics/{video_id}_BIND.md`](../../01_research/docs/chart_fanatics/{video_id}_BIND.md)  
**OpenAI aid:** [`../../../../{openai_rel}`](../../../../{openai_rel}) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family {slug}` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
**Not** STRAT-015+. **Not** NQ/US auto-inherit. **NO_PROMOTE.** Catalog `win_rate=null`.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
india_decision: {decision}
of_required: {str(of_required).lower()}
observation_gated: true
NO_PROMOTE: true
```

## One-line

{one_line or "Observation-gated India port — formalization from OpenAI suggest + BIND."}

## YAML stub

```yaml
mix_id: {mix_id}
origin: PROJECT_MIX
teacher_video: {video_id}
guest: {guest}
guest_slug: {slug}
customer_default: false
status: {status}
paper_enable: false
founder_paper_accept: false
win_rate: null
metrics: {{win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}}
of_required: {str(of_required).lower()}
india_decision: {decision}
promote: false
NO_PROMOTE: true
docs:
  - teams/01_research/docs/chart_fanatics/{video_id}_BIND.md
  - {openai_rel}
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.
"""
    path = CAND / f"{mix_id}.md"
    path.write_text(body, encoding="utf-8")
    return path


def bind_rev_block(meta: dict, suggest: dict, openai_rel: str) -> str:
    ia = suggest.get("india_adaptation") if isinstance(suggest.get("india_adaptation"), dict) else {}
    decision = (ia.get("decision") or "UNKNOWN").upper()
    banner = suggest.get("bind_honesty_banner")
    banner_txt = as_text(banner) if banner else ""
    core = as_text(suggest.get("core_edge"))[:1200]
    obs = as_text(suggest.get("observation_protocol"))[:1200]
    miss = as_text(suggest.get("miss_entry_recovery"))[:1200]
    port = as_text(suggest.get("market_portability"))[:800]
    grid = as_text(suggest.get("backtest_search_grid"))[:1000]
    models = as_text(suggest.get("entry_models"))[:1500]
    risk = as_text(suggest.get("risk_shell"))[:600]
    proposed = suggest.get("proposed_mix_ids") or []
    mix_lines = []
    if isinstance(proposed, list):
        for row in proposed[:12]:
            if isinstance(row, dict):
                mix_lines.append(
                    f"| `{row.get('mix_id')}` | {row.get('role')} | {row.get('one_line') or row.get('status_hint') or ''} |"
                )
            else:
                mix_lines.append(f"| `{row}` | ? | |")
    mix_table = "\n".join(mix_lines) if mix_lines else "| (see OpenAI JSON) | | |"

    return f"""

---

## OpenAI + India refresh — {DATE}

**OpenAI aid (HYPOTHESIS only):** [`../../../../{openai_rel}`](../../../../{openai_rel}) — does **not** fix win rates.  
**India decision:** `{decision}` · of_required={ia.get('of_required')} · ohcl_proxy_ok={ia.get('ohcl_proxy_ok')}  
**Rationale:** {ia.get('rationale') or 'see OpenAI JSON'}  
**India analogs:** {", ".join(ia.get("india_analogs") or []) or "n/a"}  
**KEEP_ALL / NO_PROMOTE** · `win_rate=null` · no STRAT-015+ · soft news veto stays parked.

### Honesty banner (rev)

```text
openai_suggest: HYPOTHESIS aid only — does not fix WR / does not VALIDATION
magnet_or_level: observable|searchable — not sacred
market_scope: teacher_examples=US/NQ/etc; portable_if_observed=HYPOTHESIS
india_decision: {decision}
catalog_win_rate: null
NO_PROMOTE: true
{banner_txt[:800]}
```

### Core edge (formalization · HYPOTHESIS)

{core or "_see OpenAI JSON_"}

### Observation protocol (HYPOTHESIS)

{obs or "_see OpenAI JSON_"}

### Entry models (HYPOTHESIS)

{models or "_see OpenAI JSON_"}

### Miss-entry / recovery (HYPOTHESIS)

{miss or "_see OpenAI JSON_"}

### Risk shell (HYPOTHESIS)

{risk or "_see OpenAI JSON_"}

### Market portability

{port or "_see OpenAI JSON_"}

### Backtest search grid (for 06)

{grid or "_see OpenAI JSON_"}

### Proposed MIX ids (KEEP_ALL)

| mix_id | role | note |
|--------|------|------|
{mix_table}

**Accepted:** observation-gated formalization; India `{decision}`; teacher WR claims null.  
**Rejected:** auto-inherit US digits/clocks/OF thresholds; STRAT-015+; claiming OpenAI fixed BT.  
**UNKNOWN / DATA_INSUFFICIENT:** timed VTT; Dhan historical OF/tape when of_required.
"""


def ensure_bind(meta: dict, suggest: dict, openai_rel: str) -> tuple[Path, str]:
    """Create new BIND or append refresh block. Returns (path, action)."""
    tid = meta["id"]
    path = CF / f"{tid}_BIND.md"
    rev = bind_rev_block(meta, suggest, openai_rel)
    marker = f"## OpenAI + India refresh — {DATE}"

    if path.is_file():
        old = path.read_text(encoding="utf-8")
        if marker in old:
            # replace prior overnight block
            pre = old.split(marker, 1)[0].rstrip()
            # drop leading --- we add in rev
            if pre.endswith("---"):
                pre = pre[: -3].rstrip()
            # also strip trailing OpenAI refresh if double
            path.write_text(pre + "\n" + rev.lstrip("\n"), encoding="utf-8")
            return path, "refreshed"
        # bump date line if present
        new = old
        if "**Date:**" in new:
            new = re.sub(
                r"\*\*Date:\*\*[^\n]+",
                f"**Date:** 2026-09-06 (rev: OpenAI+India overnight {DATE})",
                new,
                count=1,
            )
        if "**OpenAI aid" not in new:
            # insert OpenAI pointer near top after Origin/KEEP lines if possible
            insert = (
                f"**OpenAI aid (HYPOTHESIS only):** [`../../../../{openai_rel}`]"
                f"(../../../../{openai_rel}) — does **not** fix win rates.\n"
            )
            if "**KEEP_ALL:**" in new:
                new = new.replace("**KEEP_ALL:**", insert + "**KEEP_ALL:**", 1)
            else:
                new = new.rstrip() + "\n\n" + insert
        path.write_text(new.rstrip() + "\n" + rev, encoding="utf-8")
        return path, "appended"

    # New BIND (Yush / Marco-DAV)
    ia = suggest.get("india_adaptation") if isinstance(suggest.get("india_adaptation"), dict) else {}
    decision = (ia.get("decision") or "UNKNOWN").upper()
    header = f"""# BIND — `{tid}` · {meta['guest']} (Chart Fanatics)

**Team:** 01_research  
**Date:** {DATE} (OpenAI suggest + India portability pass)  
**Layer:** `SOURCE_FACT` (`ASR_WHISPER` — **not** YouTube captions) → formalization / grids = **`HYPOTHESIS`** until 06 validates  
**Video:** https://www.youtube.com/watch?v={tid}  
**MD transcript:** [`{tid}_TRANSCRIPT.md`]({tid}_TRANSCRIPT.md)  
**Timed VTT:** `DATA_INSUFFICIENT` — anchors are **ASR paragraph order**, not clocks.  
**OpenAI aid (HYPOTHESIS only):** [`../../../../{openai_rel}`](../../../../{openai_rel}) — does **not** fix win rates.  
**Origin tag for any MIX:** `EXTERNAL_RESEARCH` / Chart Fanatics guest — **not** `DHAN-DERIVED`.  
**KEEP_ALL:** do **not** club into STRAT-001–014, IQCapital MIXes, prior `MIX-CF-*` (unless same guest refine), or `MIX-DEFAULT-BUY`. **No STRAT-015+.**  
**India decision:** `{decision}`

---

## Honesty banner

```text
layer: SOURCE_FACT (transcript) / HYPOTHESIS (named MIX formalization + BT grid)
guest: {meta['guest']}
source: ASR_WHISPER faster-whisper — [ASR] caveat
india_transfer: HYPOTHESIS only — observation-gated; decision={decision}
win_rates_spoken: CLAIMS only — product win_rate=null
education: not edge
openai_suggest: HYPOTHESIS aid only
NO_PROMOTE: true
```

---

## What this is **not**

| Claim | Verdict |
|-------|---------|
| Title / guest WR as product metric | **Rejected** — `win_rate=null` |
| Silent NIFTY inherit of US levels/OF thresholds | **Rejected** |
| STRAT-015+ | **Rejected** |
| Clubbing into unrelated prior MIX without founder ask | **Rejected** |
| “OpenAI fixed the backtests” | **Rejected** |

"""
    path.write_text(header + rev, encoding="utf-8")
    return path, "created"


def collect_mixes(meta: dict, suggest: dict, openai_rel: str) -> list[dict]:
    ia = suggest.get("india_adaptation") if isinstance(suggest.get("india_adaptation"), dict) else {}
    decision = (ia.get("decision") or "UNKNOWN").upper()
    of_req = bool(ia.get("of_required"))
    out: list[dict] = []
    proposed = suggest.get("proposed_mix_ids") or []
    if not isinstance(proposed, list):
        proposed = []

    # Prefer explicit india mix ids
    in_ids = ia.get("proposed_in_mix_ids") or []
    if isinstance(in_ids, list) and in_ids:
        for mid in in_ids:
            if not isinstance(mid, str):
                continue
            mix_id = sanitize_mix_id(mid, f"{meta['mix_prefix']}-IN")
            if "-IN" not in mix_id:
                mix_id = sanitize_mix_id(f"{meta['mix_prefix']}-IN-{mid}", meta["mix_prefix"])
            path = write_india_candidate(
                mix_id,
                guest=meta["guest"],
                video_id=meta["id"],
                slug=meta["slug"],
                teacher_hint=meta["mix_prefix"],
                one_line=as_text(suggest.get("core_edge"))[:240],
                of_required=of_req,
                decision=decision,
                openai_rel=openai_rel,
            )
            out.append({"mix_id": mix_id, "path": str(path.relative_to(ROOT)), "role": "india", "decision": decision})
        return out

    # From proposed_mix_ids where role india or mix contains -IN-
    for row in proposed:
        if not isinstance(row, dict):
            continue
        role = (row.get("role") or "").lower()
        mid = str(row.get("mix_id") or "")
        if role not in ("india", "adaptation", "port") and "-IN-" not in mid.upper() and not mid.upper().endswith("-IN"):
            continue
        mix_id = sanitize_mix_id(mid, f"{meta['mix_prefix']}-IN")
        path = write_india_candidate(
            mix_id,
            guest=meta["guest"],
            video_id=meta["id"],
            slug=meta["slug"],
            teacher_hint=meta["mix_prefix"],
            one_line=str(row.get("one_line") or "")[:240],
            of_required=of_req,
            decision=decision,
            openai_rel=openai_rel,
        )
        out.append({"mix_id": mix_id, "path": str(path.relative_to(ROOT)), "role": "india", "decision": decision})

    # If PORT/PARTIAL but nothing proposed, create a default IN-CORE
    if not out and decision in ("PORT", "PARTIAL"):
        mix_id = f"{meta['mix_prefix']}-IN-CORE"
        path = write_india_candidate(
            mix_id,
            guest=meta["guest"],
            video_id=meta["id"],
            slug=meta["slug"],
            teacher_hint=meta["mix_prefix"],
            one_line=as_text(suggest.get("core_edge"))[:240],
            of_required=of_req,
            decision=decision,
            openai_rel=openai_rel,
        )
        out.append({"mix_id": mix_id, "path": str(path.relative_to(ROOT)), "role": "india", "decision": decision})

    # Teacher mixes for brand-new guests (YUSH / MARCO-DAV)
    if meta["slug"] in ("YUSH", "MARCO-DAV"):
        for row in proposed:
            if not isinstance(row, dict):
                continue
            role = (row.get("role") or "teacher").lower()
            mid = str(row.get("mix_id") or "")
            if role == "india" or "-IN-" in mid.upper():
                continue
            mix_id = sanitize_mix_id(mid or f"{meta['mix_prefix']}-CORE", meta["mix_prefix"])
            # teacher candidate
            status = "DATA_INSUFFICIENT" if of_req and "OF" in mix_id.upper() else "BACKTEST_BOOK"
            body = f"""# {mix_id} — {meta['guest']} teacher book

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `{status}`  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `{meta['id']}`  
**Bind:** [`../../01_research/docs/chart_fanatics/{meta['id']}_BIND.md`](../../01_research/docs/chart_fanatics/{meta['id']}_BIND.md)  
**OpenAI aid:** [`../../../../{openai_rel}`](../../../../{openai_rel})  
**Not** STRAT-015+. **KEEP_ALL** vs prior Marco/Yush-less catalog. **NO_PROMOTE.** `win_rate=null`.

```yaml
mix_id: {mix_id}
origin: EXTERNAL_RESEARCH
origin_videos: [{{video_id: {meta['id']}, channel: chart-fanatics, guest: {meta['guest']}}}]
customer_default: false
status: {status}
win_rate: null
asr_caveat: true
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-OKALA-8020-LEVEL]
```

{row.get('one_line') or as_text(suggest.get('core_edge'))[:400]}
"""
            p = CAND / f"{mix_id}.md"
            p.write_text(body, encoding="utf-8")
            out.append({"mix_id": mix_id, "path": str(p.relative_to(ROOT)), "role": "teacher", "decision": decision})

    return out


def write_skips(skips: list[dict]) -> Path:
    lines = [
        f"# CF overnight skips — {DATE}",
        "",
        "**Layer:** research triage. Soft news veto stays parked. **NO_PROMOTE.**",
        "",
        "US prop / OF / DOM / session-clock strategies without a clear India/Dhan analog are listed here.",
        "PARTIAL rows may still get OHLC-proxy `MIX-*-IN-*` with honesty banners.",
        "",
        "| video_id | guest | decision | reason |",
        "|----------|-------|----------|--------|",
    ]
    for s in skips:
        reason = (s.get("reason") or "").replace("|", "/").replace("\n", " ")[:200]
        lines.append(
            f"| `{s.get('id')}` | {s.get('guest')} | {s.get('decision')} | {reason} |"
        )
    if not skips:
        lines.append("| — | — | — | (none yet) |")
    lines.append("")
    lines.append("## HANDOFF")
    lines.append("")
    lines.append("- **Accepted:** SKIP/PARTIAL honesty for non-portable OF/US-clock books.")
    lines.append("- **Rejected:** inventing Dhan OF history; re-enabling soft news veto.")
    lines.append("- **UNKNOWN:** future ASR unlocks from workstream B.")
    path = RECON / f"CF_OVERNIGHT_SKIPS_{DATE}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*")
    args = ap.parse_args()

    selected = list(VIDEOS)
    if args.ids:
        want = set(args.ids)
        selected = [v for v in selected if v["id"] in want]

    summary: dict[str, Any] = {
        "as_of": DATE,
        "binds": [],
        "mixes": [],
        "skips": [],
        "openai_missing": [],
        "openai_ok": 0,
    }

    for meta in selected:
        slug = meta["slug"]
        suggest = load_suggest(slug)
        openai_rel = f"data/recon/CF_OPENAI_{slug}_BIND_SUGGEST_{DATE}.md"
        if suggest is None:
            summary["openai_missing"].append(meta["id"])
            continue
        summary["openai_ok"] += 1
        path, action = ensure_bind(meta, suggest, openai_rel)
        summary["binds"].append({"id": meta["id"], "slug": slug, "action": action, "path": str(path.relative_to(ROOT))})
        mixes = collect_mixes(meta, suggest, openai_rel)
        summary["mixes"].extend(mixes)
        ia = suggest.get("india_adaptation") if isinstance(suggest.get("india_adaptation"), dict) else {}
        decision = (ia.get("decision") or "UNKNOWN").upper()
        if decision in ("SKIP", "PARTIAL"):
            summary["skips"].append(
                {
                    "id": meta["id"],
                    "guest": meta["guest"],
                    "decision": decision,
                    "reason": ia.get("rationale") or as_text(suggest.get("skip_reasons"))[:300],
                }
            )

    # Okala already done — note in skips/summary only if not present
    summary["okala_note"] = "jsUTbjwpFVk / MIX-CF-OKALA-IN-* already shipped earlier 2026-09-07 — not rematerialized."

    skips_path = write_skips(summary["skips"])
    summary["skips_path"] = str(skips_path.relative_to(ROOT))
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    out = RECON / f"CF_OVERNIGHT_C_SUMMARY_{DATE}.json"
    out.write_text(jdump(summary) + "\n", encoding="utf-8")
    print(jdump({"binds": len(summary["binds"]), "mixes": len(summary["mixes"]), "skips": len(summary["skips"]), "missing": summary["openai_missing"], "summary": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
