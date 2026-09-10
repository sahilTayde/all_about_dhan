"""One-off org counsel. Never prints keys. Writes a markdown review."""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "teams/00_orchestrator/docs/COUNSEL_ORG_2026-09-09.md"
_CTX = ssl.create_default_context()


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.is_file():
        return
    for raw in env.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _http(url: str, headers: dict, body: bytes) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90, context=_CTX) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:1200]
    except Exception as exc:  # noqa: BLE001
        return 0, type(exc).__name__


def gemini(prompt: str, model: str, key: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 2500, "temperature": 0.2},
        }
    ).encode()
    code, raw = _http(url, {"Content-Type": "application/json"}, payload)
    if code != 200:
        return {"ok": False, "gap": f"gemini HTTP {code}", "text": raw[:400]}
    try:
        blob = json.loads(raw)
        text = blob["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return {"ok": False, "gap": "gemini unparsed", "text": ""}
    return {"ok": True, "text": str(text).strip(), "model": model}


def openai(prompt: str, model: str, key: str) -> dict:
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": 2500,
        }
    ).encode()
    code, raw = _http(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        payload,
    )
    if code != 200:
        return {"ok": False, "gap": f"openai HTTP {code}", "text": raw[:400]}
    try:
        blob = json.loads(raw)
        text = blob["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return {"ok": False, "gap": "openai unparsed", "text": ""}
    return {"ok": True, "text": str(text).strip(), "model": model}


FACTS = """
Cited facts (this workspace, 2026-09-09):
- Product: DhanHQ-only NIFTY/BANKNIFTY/SENSEX index-options CE/PE BUY-first signal desk.
- Gate: NOT RESEARCH_READY_FOR_PROGRAMMING. ExecutionClient always refuses live orders.
- Roster 00-09 exists: 00 orchestrator/boss, 01 research/YouTube, 02 PhD math, 03 PhD market+CAS, 04 quant/MIX/STRATs, 05 desk-intel/customer talk, 06 backtest+retune gate, 07 coding (apps/web+api), 08 testing, 09 review+Docs Auditor.
- KEEP_ALL STRAT-001-014 UNVALIDATED. MIX-DEFAULT-BUY is customer default hypothesis. No STRAT-015+.
- RAG today: packages/agent_rag SQLite FTS5, NOT embeddings/vector. Separate transcripts.sqlite.
- Paper agents sqlite exists locally; do not git-add. Nightly emits RETUNE_PROPOSAL BACKTEST_REQUIRED, no auto-retune.
- Dashboard / is MOCK customer ticket; /desk is research. No founder PM health canvas. Counsel module can ping Gemini+OpenAI.
- Backtests so far FAIL / DATA_INSUFFICIENT. Five-pass FAILED REVIEW 2026-09-06.
- Founder example of a bad ticket: strike ~150, SL 96, target 250 on NIFTY call — target never realistic; dealer should kill/exit.
- Founder wants a real product company like Stratzy / Algoji / GoCharting Quantman, not a 'paper-trading toy' brand. Internal validation may stay paper/shadow.
- Token policy wanted: retrieve KB from RAG/SQL/local ML; burn tokens mainly for pre/post market analysis and to audit whether models/signals are sane.
"""

PROMPT = """
Role: review. India index-options product company (signal portal + research factory).
PAPER/shadow execution until review gate. No invented win rates. No live orders.
First line MUST be one of: AGREE / AGREE_WITH_CAVEATS / DISAGREE / HOLD / DATA_INSUFFICIENT.

Founder wants FIVE company departments (not replace SDLC, overlay it):
1) Engineering/Coding: RAG, SQL warehouse (candles, chain, P/L, research provenance), coding docs, local ML so agents do not re-read books every time, nightly batch (review + docs + vector/SQL + code + backtest). Each coding SECTION has a boss who may confirm with OpenAI+Gemini.
2) Analyst faculty: PhD Math, PhD Algo, PhD Statistics, PhD Market, PhD Quant. Deep reason. If a book fails they must propose parameter/regime changes, not only FAIL. Books assigned per chair. One analyst boss coordinates.
3) Documentation agent: processes, progress, next actions, how agents talk, skills, bosses, pending work, founder service URLs.
4) Monitoring / Project Manager: founder talks ONLY to PM. Colored canvas of who is working, services up, next action, critical errors (OpenAI/Gemini/Dhan key expiry, rate limits, pull failures).
5) Front desk customer portal: dealer intelligence. Talks to department bosses + OpenAI+Gemini. Learns from mistakes. Must not keep dead tickets (example: 150/96/250 NIFTY CE). Can club with monitoring site.

Questions — answer each in 3-8 lines:
Q1: Keep 00-09 teams and overlay 5 departments, or renumber/delete teams? Why?
Q2: Where should PhD Algo and PhD Statistics sit (new folders vs roles under 02/04/06)?
Q3: SQLite warehouse now vs MySQL now? Vector embeddings now vs FTS5 + later sqlite-vec?
Q4: What must the nightly batch do vs must NOT do (retune gate)?
Q5: Front desk vs PM canvas: one site two tabs, or two apps?
Q6: Token budget: what is allowed to call LLMs vs must be local RAG/ML?
Q7: How should the dealer kill unrealistic SL/target (feasibility rules) without inventing fills?
Q8: Product language: call this a signal company (Stratzy class) while keeping no-live-orders until gate — AGREE or not?
Q9: Name the 5 department bosses and who the founder talks to daily.
Q10: Top 3 risks if we implement this org poorly.

Be concrete. Cite DATA_INSUFFICIENT instead of inventing our P/L.
"""


def main() -> int:
    _load_dotenv()
    gkey = (os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY") or "").strip()
    okey = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or "").strip()
    gmodel = (os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite").strip()
    omodel = (os.getenv("OPENAI_MODEL") or "gpt-5.4-nano").strip()
    full = (
        "Role: review. PAPER only. No win rates as fact. No live orders.\n"
        f"Cited facts:\n{FACTS}\n\n{PROMPT}"
    )
    g = (
        gemini(full, gmodel, gkey)
        if len(gkey) > 8
        else {"ok": False, "gap": "GEMINI_KEY missing", "text": "", "model": gmodel}
    )
    o = (
        openai(full, omodel, okey)
        if len(okey) > 8
        else {"ok": False, "gap": "OPENAI_API_KEY missing", "text": "", "model": omodel}
    )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Dual-model counsel — company departments (2026-09-09)",
        "",
        f"**UTC:** `{now}`",
        "**Policy:** review only. Keys never printed. No live orders. **NO_PROMOTE.**",
        "",
        f"- Gemini ok={g.get('ok')} model=`{g.get('model') or gmodel}` gap=`{g.get('gap') or ''}`",
        f"- OpenAI ok={o.get('ok')} model=`{o.get('model') or omodel}` gap=`{o.get('gap') or ''}`",
        "",
        "## Gemini",
        "",
        g.get("text") or f"_failed: {g.get('gap')}_",
        "",
        "## OpenAI",
        "",
        o.get("text") or f"_failed: {o.get('gap')}_",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} gemini_ok={g.get('ok')} openai_ok={o.get('ok')}")
    return 0 if (g.get("ok") or o.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
