#!/usr/bin/env python3
"""Overnight CF OpenAI BIND suggest batch (PAPER / HYPOTHESIS only).

Usage:
  .venv/bin/python scripts/cf_openai_bind_batch.py            # all usable except Okala
  .venv/bin/python scripts/cf_openai_bind_batch.py --ids hvyf6frvCcA T_djSNBmV00
  .venv/bin/python scripts/cf_openai_bind_batch.py --include-okala

Never prints API keys. Writes data/recon/CF_OPENAI_<GUEST>_BIND_SUGGEST_2026-09-07.{md,json}
plus data/recon/CF_OPENAI_BATCH_STATUS_2026-09-07.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CF = ROOT / "teams/01_research/docs/chart_fanatics"
RECON = ROOT / "data/recon"
DATE = "2026-09-07"
MAX_CHARS_TRANSCRIPT = 28_000
MAX_CHARS_BIND = 18_000

# Usable full transcripts (CHANNEL_INVENTORY yes=18). Okala already has OpenAI suggest.
VIDEOS: list[dict] = [
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
    {"id": "jsUTbjwpFVk", "guest": "Okala", "slug": "OKALA", "mix_prefix": "MIX-CF-OKALA"},
]


def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_caption_body(md: str) -> str:
    marker = "## Caption text"
    if marker in md:
        body = md.split(marker, 1)[1]
    else:
        body = md
    # drop leading [ASR] note line if present
    lines = body.strip().splitlines()
    if lines and lines[0].startswith("[ASR]"):
        lines = lines[1:]
    return collapse_ws("\n".join(lines))


def truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 20] + "\n…[truncated]…"


def out_paths(slug: str) -> tuple[Path, Path]:
    base = f"CF_OPENAI_{slug}_BIND_SUGGEST_{DATE}"
    return RECON / f"{base}.md", RECON / f"{base}.json"


def system_prompt() -> str:
    return """You are a research desk assistant for an India index-options PAPER signal company (DhanHQ research only).
Hard rules:
- PAPER / NO_PROMOTE. Never invent win rates, fills, lot sizes, or Dhan quotes.
- Layers: transcript quotes = SOURCE_FACT; creative formalization / India port = HYPOTHESIS until VALIDATION.
- Teacher / title WR claims stay claims only (win_rate=null until BT).
- Do NOT claim OpenAI suggestions fix backtest win rates.
- Levels/magnets/round numbers are OBSERVATIONS — not sacred constants; desk may re-observe per market.
- Capture miss-entry / no-chase / recovery rules richly when spoken.
- Prefer structuring a searchable BT parameter grid for 06.
- India markets in scope: NIFTY / BANKNIFTY / SENSEX index options CE/PE buy-first.
- If US prop / order-flow / DOM / Sierra / MotiveWave specifics lack an India/Dhan analog, mark india_adaptation.decision=SKIP (or PARTIAL with OHLC-only proxy).
- KEEP_ALL: do not delete prior MIX; propose NEW MIX-CF-<GUEST>-* or MIX-CF-<GUEST>-IN-* ids; never STRAT-015+.
- Soft news veto is parked (NEWS_VETO_ENABLED=false) — do not re-enable in suggestions.
Return a single JSON object with keys:
guest_slug, video_id, core_edge, observation_protocol, entry_models, miss_entry_recovery,
session_filters, risk_shell, market_portability, india_adaptation, proposed_mix_ids,
backtest_search_grid, risks_overfit, bind_honesty_banner, skip_reasons
india_adaptation must include: decision (PORT|PARTIAL|SKIP), rationale, india_analogs (list),
proposed_in_mix_ids (list), of_required (bool), ohcl_proxy_ok (bool).
proposed_mix_ids: list of {mix_id, role (teacher|india), one_line, status_hint}.
Be concrete within honesty. No secrets.
"""


def user_prompt(meta: dict, transcript: str, bind: str | None) -> str:
    bind_block = bind if bind else "(no BIND yet — create first formalization from transcript)"
    return f"""Improve / create BIND formalization + India adaptation plan for Chart Fanatics guest.

VIDEO_ID: {meta['id']}
GUEST: {meta['guest']}
GUEST_SLUG: {meta['slug']}
EXISTING_MIX_PREFIX: {meta['mix_prefix']}
FOUNDER INTENT:
- Observation-gated levels/magnets (not sacred).
- Miss-entry / recovery rules when spoken.
- India port = separate MIX-*-IN-* when portable; else SKIP with reason.
- New MIX per distinct video/book if needed (esp. Marco return DaVinci ≠ prior Marco liq-trap; Yush new).
- win_rate=null · NO_PROMOTE · no STRAT-015+.

TRANSCRIPT (collapsed, may truncate):
{transcript}

CURRENT BIND (may be empty):
{bind_block}
"""


def call_openai(meta: dict, model: str) -> dict:
    from openai import OpenAI

    tid = meta["id"]
    slug = meta["slug"]
    trans_path = CF / f"{tid}_TRANSCRIPT.md"
    bind_path = CF / f"{tid}_BIND.md"
    if not trans_path.is_file():
        return {"ok": False, "error": "missing_transcript", "id": tid, "slug": slug}

    transcript = truncate(extract_caption_body(trans_path.read_text(encoding="utf-8")), MAX_CHARS_TRANSCRIPT)
    bind = None
    if bind_path.is_file():
        bind = truncate(bind_path.read_text(encoding="utf-8"), MAX_CHARS_BIND)

    key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or "").strip()
    if not key:
        return {"ok": False, "error": "missing_openai_key", "id": tid, "slug": slug}

    client = OpenAI(api_key=key, timeout=240.0, max_retries=1)
    # gpt-5.4-nano requires max_completion_tokens
    params: dict = {"model": model, "max_completion_tokens": 7000}
    resp = client.chat.completions.create(
        **params,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": user_prompt(meta, transcript, bind)},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    finish = getattr(resp.choices[0], "finish_reason", None)
    usage = getattr(resp, "usage", None)
    usage_note = ""
    if usage is not None:
        usage_note = (
            f"prompt_tokens={getattr(usage, 'prompt_tokens', None)} "
            f"completion_tokens={getattr(usage, 'completion_tokens', None)}"
        )
    if not text:
        return {
            "ok": False,
            "error": "empty_response",
            "id": tid,
            "slug": slug,
            "finish": finish,
            "usage": usage_note,
        }
    parsed = json.loads(text)
    md_path, json_path = out_paths(slug)
    pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
    json_path.write_text(pretty + "\n", encoding="utf-8")
    body = (
        f"# CF OpenAI {meta['guest']} BIND suggestions — {DATE}\n\n"
        f"**Status:** OK\n"
        f"**Video:** `{tid}`\n"
        f"**Guest slug:** `{slug}`\n"
        f"**Model:** `{model}`\n"
        f"**finish_reason:** {finish}\n"
        f"**Usage:** {usage_note or 'n/a'}\n"
        f"**Layer:** OpenAI output = `HYPOTHESIS` formalization aid — not VALIDATION; does not fix win rates.\n"
        f"**Input:** collapsed transcript (+ BIND if present). No API keys.\n"
        f"**Param note:** used `max_completion_tokens` (gpt-5.4-nano rejects `max_tokens`).\n"
        f"**NO_PROMOTE** · PAPER / research only.\n\n"
        f"## Suggested JSON\n\n```json\n{pretty}\n```\n\n"
        f"**No secrets.**\n"
    )
    md_path.write_text(body, encoding="utf-8")
    decision = None
    ia = parsed.get("india_adaptation") if isinstance(parsed, dict) else None
    if isinstance(ia, dict):
        decision = ia.get("decision")
    return {
        "ok": True,
        "id": tid,
        "slug": slug,
        "guest": meta["guest"],
        "finish": finish,
        "usage": usage_note,
        "india_decision": decision,
        "md": str(md_path.relative_to(ROOT)),
        "json": str(json_path.relative_to(ROOT)),
        "keys": list(parsed.keys()) if isinstance(parsed, dict) else [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", help="Restrict to video ids")
    ap.add_argument("--include-okala", action="store_true")
    ap.add_argument("--sleep", type=float, default=1.5, help="Seconds between calls")
    ap.add_argument("--force", action="store_true", help="Re-run even if suggest json exists")
    args = ap.parse_args()

    load_env()
    model = (os.getenv("OPENAI_MODEL") or "gpt-5.4-nano").strip()
    RECON.mkdir(parents=True, exist_ok=True)

    selected = list(VIDEOS)
    if not args.include_okala:
        selected = [v for v in selected if v["id"] != "jsUTbjwpFVk"]
    if args.ids:
        want = set(args.ids)
        selected = [v for v in selected if v["id"] in want]

    status_path = RECON / f"CF_OPENAI_BATCH_STATUS_{DATE}.json"
    prior = {}
    if status_path.is_file():
        try:
            prior = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior = {}
    results = list(prior.get("results") or [])
    done_ids = {r.get("id") for r in results if r.get("ok")}

    print(f"model={model} n={len(selected)} force={args.force}", flush=True)
    ok_n = fail_n = skip_n = 0

    for i, meta in enumerate(selected, 1):
        tid = meta["id"]
        md_path, json_path = out_paths(meta["slug"])
        if not args.force and tid in done_ids and json_path.is_file():
            print(f"[{i}/{len(selected)}] SKIP already-ok {tid} {meta['slug']}", flush=True)
            skip_n += 1
            continue
        if not args.force and json_path.is_file() and tid not in (args.ids or []):
            # resume-friendly: count existing as ok without re-call unless --force
            print(f"[{i}/{len(selected)}] SKIP file-exists {tid} {meta['slug']}", flush=True)
            # ensure in results
            if tid not in {r.get("id") for r in results}:
                try:
                    blob = json.loads(json_path.read_text(encoding="utf-8"))
                    ia = blob.get("india_adaptation") if isinstance(blob, dict) else {}
                    results.append(
                        {
                            "ok": True,
                            "id": tid,
                            "slug": meta["slug"],
                            "guest": meta["guest"],
                            "india_decision": (ia or {}).get("decision") if isinstance(ia, dict) else None,
                            "md": str(md_path.relative_to(ROOT)),
                            "json": str(json_path.relative_to(ROOT)),
                            "resumed_from_disk": True,
                        }
                    )
                except Exception as e:  # noqa: BLE001
                    results.append({"ok": False, "id": tid, "slug": meta["slug"], "error": f"read_existing:{e}"})
            skip_n += 1
            continue

        print(f"[{i}/{len(selected)}] CALL {tid} {meta['slug']}…", flush=True)
        try:
            row = call_openai(meta, model)
        except Exception as e:  # noqa: BLE001
            row = {"ok": False, "id": tid, "slug": meta["slug"], "guest": meta["guest"], "error": str(e)[:400]}
        # replace prior row for same id
        results = [r for r in results if r.get("id") != tid] + [row]
        if row.get("ok"):
            ok_n += 1
            print(f"  OK india={row.get('india_decision')} {row.get('usage')}", flush=True)
        else:
            fail_n += 1
            print(f"  FAIL {row.get('error')}", flush=True)
        status = {
            "as_of": DATE,
            "model": model,
            "ok": sum(1 for r in results if r.get("ok")),
            "fail": sum(1 for r in results if not r.get("ok")),
            "results": results,
        }
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        if i < len(selected) and args.sleep > 0:
            time.sleep(args.sleep)

    print(json.dumps({"batch_ok": ok_n, "batch_fail": fail_n, "batch_skip": skip_n, "status": str(status_path)}))
    return 0 if fail_n == 0 or ok_n > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
