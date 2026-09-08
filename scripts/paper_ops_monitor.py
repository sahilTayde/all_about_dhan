#!/usr/bin/env python3
"""Lightweight PAPER ops monitor — rewrites paper-operations-monitor.canvas.tsx.

Production-like PAPER signal generation (NOT live orders).
Rewrites canvas every ~20–30s. Never prints secrets. NO_PROMOTE.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER_DIR = ROOT / "data" / "recon" / "paper_ledger"
RECON = ROOT / "data" / "recon"
PID_FILE = RECON / "paper_ops_pids.json"
STATUS_FILE = RECON / "paper_ops_monitor_status.json"
RESTART_FLAG = RECON / "paper_ops_restart_once.flag"
KB_PATH = ROOT / "data" / "knowledge" / "trading_agents_india.sqlite"
CANVAS = Path(
    "/Users/sahiltayde/.cursor/projects/"
    "Users-sahiltayde-Documents-all-about-dhan/canvases/"
    "paper-operations-monitor.canvas.tsx"
)
LOG_CANDIDATES = [
    RECON / "paper_market_hours_ops.log",
    RECON / "paper_market_hours_current.log",
]
MONITOR_LOG = RECON / "paper_ops_monitor.log"
VENV_PY = ROOT / ".venv" / "bin" / "python"


def _ist_now() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _port_up(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _load_pids() -> dict:
    if not PID_FILE.exists():
        return {}
    try:
        return json.loads(PID_FILE.read_text())
    except Exception:
        return {}


def _save_pids(pids: dict) -> None:
    PID_FILE.write_text(json.dumps(pids, indent=2) + "\n")


def _ledger_day_path() -> Path:
    try:
        from zoneinfo import ZoneInfo

        day = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    except Exception:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return LEDGER_DIR / f"{day}.jsonl"


def _bucket_di_gap(gap: str) -> str:
    """Map a ledger data_gap string into a founder-facing WHY bucket."""
    g = str(gap or "")
    gl = g.lower()
    if "no paper evaluator bound" in gl or (
        "evaluator" in gl and "bound" in gl
    ):
        return "unbound STRAT evaluators (catalog observed, no PAPER binder)"
    if "underdefined" in gl or ("stop" in gl and "premium" in gl):
        return "Stop/premium UNDERDEFINED (refusing index-as-premium)"
    if "optidx" in gl or "premium" in gl or "index proxy" in gl:
        return "Option premium / OPTIDX gaps (LTP unbound or INDEX proxy)"
    if "dhan" in gl or "live chain" in gl or "chain error" in gl:
        return "Dhan gaps (chain/API errors or dry fixtures)"
    if "openai" in gl or "llm" in gl:
        return "LLM/OpenAI call failures (fallback → DI, not promote)"
    if "news" in gl or "sentiment" in gl or "social" in gl or "stocktwits" in gl:
        return "News/sentiment feeds unwired (hold ticket, not alpha)"
    if "event_memory" in gl or "analog" in gl:
        return "EVENT_MEMORY analogs empty"
    if "hold" in gl:
        return "HOLD lean / directional suppress"
    return "Other DATA_INSUFFICIENT gaps"


def _bucket_signal_reason(reason: str) -> str | None:
    """Map SIGNAL reason → founder veto label. None = skip (persona/meta chatter)."""
    r = str(reason or "")
    rl = r.lower()
    head = r.split(":", 1)[0].strip().lower() if ":" in r else ""
    if "news_day" in rl or "macro_event" in rl:
        return "NEWS_DAY / MACRO_EVENT hold"
    if "dead-band" in rl or "session_clock" in rl or "mix-clock" in rl:
        return "Clock dead-band / outside shell"
    if "dhan" in rl and ("chain" in rl or "api" in rl):
        return "Chain / Dhan gap (fixture fallback)"
    if head == "boss" or "boss desk" in rl:
        return "Boss desk HOLD"
    if head == "tech" or r.startswith("tech:"):
        return "Technical / chain lean (confirm-kill)"
    if "veto" in rl or (head == "stage" and "hold" in rl):
        return "Stage VETOED"
    if head == "cited_news":
        return "Cited news overlay (hold ticket)"
    # Skip debate/persona/meta keys that flood every SIGNAL
    if head in {
        "bull",
        "bear",
        "trader",
        "risk",
        "sentiment",
        "news",
        "input_mix",
        "phd_note",
        "provenance",
        "chain",
    }:
        return None
    return None


def _state_tone(state: object) -> str:
    """Map process/outcome labels → TableRowTone / StatTone family."""
    s = str(state or "").strip().upper()
    if s in {"DOWN", "DEAD", "ERROR", "CRASHED", "REFUSED"}:
        return "danger"
    if s in {"RUNNING", "OPEN", "OK", "UP", "ALLOW", "ON"}:
        return "success"
    if (
        "DATA_INSUFFICIENT" in s
        or s in {"STALE", "IDLE", "OUTSIDE", "DI", "OFF"}
        or s.startswith("DI")
    ):
        return "warning"
    if s in {"HOLD", "WAITING", "PENDING", "WATCH"}:
        return "info"
    return "neutral"


def _count_ledger(path: Path) -> dict:
    out = {
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "lines": 0,
        "signals": 0,
        "shadow": 0,
        "shadow_open": 0,
        "shadow_skipped": 0,
        "paper_trade": 0,
        "non_hold_signals": 0,
        "candidates": 0,
        "di_count": 0,
        "di_hold_lean": 0,
        "di_unbound_evaluator": 0,
        "di_buckets": {},
        "di_gap_top": [],
        "signal_sides": {},
        "shadow_statuses": {},
        "candidate_outcomes": {},
        "signal_reason_top": [],
        "last_as_of_ist": None,
        "last_event_type": None,
        "parse_errors": 0,
    }
    if not path.exists():
        return out
    sides: Counter[str] = Counter()
    shadow_status: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    buckets: Counter[str] = Counter()
    gap_raw: Counter[str] = Counter()
    reason_buckets: Counter[str] = Counter()
    last = None
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out["lines"] += 1
            try:
                obj = json.loads(line)
            except Exception:
                out["parse_errors"] += 1
                continue
            last = obj
            et = obj.get("event_type") or "?"
            if et == "SIGNAL":
                out["signals"] += 1
                side = (
                    obj.get("lean")
                    or obj.get("side")
                    or obj.get("decision")
                    or obj.get("action")
                    or obj.get("bias")
                )
                entry = obj.get("entry")
                if not side and isinstance(entry, dict):
                    side = entry.get("side") or entry.get("lean")
                side_s = str(side or "?")
                sides[side_s] += 1
                if side_s.upper() not in ("HOLD", "?", "NONE", ""):
                    out["non_hold_signals"] += 1
                seen_rb: set[str] = set()
                for raw in obj.get("reasons") or []:
                    b = _bucket_signal_reason(str(raw))
                    if not b or b in seen_rb:
                        continue
                    reason_buckets[b] += 1
                    seen_rb.add(b)
            elif et == "SHADOW_TRADE":
                out["shadow"] += 1
                st = str(obj.get("status") or "?")
                shadow_status[st] += 1
                if st == "SHADOW_OPEN":
                    out["shadow_open"] += 1
                elif st == "SHADOW_SKIPPED":
                    out["shadow_skipped"] += 1
            elif et == "PAPER_TRADE":
                out["paper_trade"] += 1
            elif et == "CANDIDATE_OBSERVATION":
                out["candidates"] += 1
                oc = str(obj.get("outcome") or "?")
                outcomes[oc] += 1
                if oc == "DATA_INSUFFICIENT":
                    out["di_count"] += 1
                    lean = str(
                        obj.get("final_lean") or obj.get("raw_lean") or ""
                    ).upper()
                    if lean == "HOLD":
                        out["di_hold_lean"] += 1
                    prov = obj.get("provenance") or {}
                    if prov.get("candidate_evaluator_available") is False:
                        out["di_unbound_evaluator"] += 1
                    gaps = obj.get("data_gaps") or []
                    if not gaps and isinstance(obj.get("freshness"), dict):
                        gaps = obj["freshness"].get("data_gaps") or []
                    seen_bucket: set[str] = set()
                    for g in gaps:
                        gs = str(g)
                        gap_raw[gs[:140]] += 1
                        b = _bucket_di_gap(gs)
                        if b not in seen_bucket:
                            buckets[b] += 1
                            seen_bucket.add(b)
    if last:
        out["last_as_of_ist"] = last.get("as_of_ist")
        out["last_event_type"] = last.get("event_type")
    out["signal_sides"] = dict(sides)
    out["shadow_statuses"] = dict(shadow_status)
    out["candidate_outcomes"] = dict(outcomes)
    out["di_buckets"] = dict(buckets)
    out["di_gap_top"] = [
        {"gap": g, "count": c} for g, c in gap_raw.most_common(8)
    ]
    out["signal_reason_top"] = [
        {"reason": r, "count": c} for r, c in reason_buckets.most_common(6)
    ]
    return out


def _di_why_rows(
    ledger: dict,
    clock: dict,
    llm: dict,
    website_up: bool,
    api_up: bool,
    leans: dict,
    section_ts: str,
) -> list[list[str]]:
    """Compact DI honesty rows (canvas collapsed). Top causes only — no flood."""
    del clock, llm, website_up, api_up, leans  # kept for call-site compatibility
    rows: list[list[str]] = []
    di = int(ledger.get("di_count") or 0)
    cand = int(ledger.get("candidates") or 0)
    ratio = f"{(100.0 * di / cand):.0f}%" if cand else "n/a"
    unbound = int(ledger.get("di_unbound_evaluator") or 0)
    if unbound:
        rows.append(
            [
                "Unbound STRAT-001..014",
                str(unbound),
                "No PAPER binder (KEEP_ALL) — honesty DI, not catalog delete",
            ]
        )
    rows.append(
        [
            "DI / candidates",
            f"{di} / {cand} ({ratio})",
            "Mass DI ≈ unbound evaluators when ratio is high",
        ]
    )
    vetoed = int((ledger.get("candidate_outcomes") or {}).get("VETOED") or 0)
    if vetoed:
        rows.append(
            [
                "VETOED (bound MIX only)",
                str(vetoed),
                "Evaluated then vetoed — not DI",
            ]
        )
    for bucket, count in sorted(
        (ledger.get("di_buckets") or {}).items(), key=lambda x: -x[1]
    )[:2]:
        # Skip restating unbound if already first row
        if "unbound" in str(bucket).lower() and unbound:
            continue
        # Skip buckets that merely echo the unbound mass (noise)
        if unbound and int(count) >= max(1, int(0.9 * unbound)):
            continue
        rows.append([str(bucket)[:48], str(count), "Top DI bucket (honesty)"])
    rows.append(
        [
            "Promote",
            "false",
            "NO_PROMOTE · not RESEARCH_READY_FOR_PROGRAMMING",
        ]
    )
    return rows[:5]


def _side_counts(sides: dict | None) -> tuple[int, int, int]:
    """Ledger SIGNAL.lean is BUY_CE/BUY_PE/HOLD — do not look for bare CE/PE."""
    hold = ce = pe = 0
    for raw, n in (sides or {}).items():
        key = str(raw or "").upper()
        count = int(n or 0)
        if key in ("HOLD", "NONE", "?", ""):
            hold += count
        elif key in ("BUY_CE", "CE", "CALL", "BUY_CALL"):
            ce += count
        elif key in ("BUY_PE", "PE", "PUT", "BUY_PUT"):
            pe += count
    return hold, ce, pe


def _veto_rows(ledger: dict, clock: dict, section_ts: str) -> list[list[str]]:
    """Top customer-ticket veto / HOLD reasons — primary canvas table."""
    rows: list[list[str]] = []
    sig = int(ledger.get("signals") or 0)
    sides = ledger.get("signal_sides") or {}
    hold = int(sides.get("HOLD") or 0)
    for item in ledger.get("signal_reason_top") or []:
        rows.append(
            [
                str(item.get("reason") or "reason"),
                str(item.get("count") or 0),
                "SIGNAL reasons bucket (why ticket stayed HOLD)",
            ]
        )
    vetoed = int((ledger.get("candidate_outcomes") or {}).get("VETOED") or 0)
    if vetoed:
        rows.append(
            [
                "Bound MIX evaluator VETOED",
                str(vetoed),
                "Only PAPER-bound candidates — vetoed, not DI",
            ]
        )
    if hold and sig:
        rows.append(
            [
                "Customer lean HOLD",
                f"{hold} / {sig}",
                section_ts,
            ]
        )
    if not clock.get("allow_directional_paper"):
        rows.append(
            [
                "Directional paper suppressed",
                "HOLD",
                str(clock.get("reason") or "dead-band / outside allow window")[:120],
            ]
        )
    if not rows:
        rows.append(["None yet", "—", f"{section_ts} · waiting for SIGNAL rows"])
    return rows[:6]


def _log_meta() -> dict:
    best = None
    for p in LOG_CANDIDATES:
        if p.exists():
            if best is None or p.stat().st_mtime > best.stat().st_mtime:
                best = p
    if best is None:
        return {
            "path": None,
            "bytes": 0,
            "mtime": None,
            "age_seconds": None,
            "tail_hint": "missing",
            "last_openai_used": None,
            "last_tick": None,
            "last_llm_error_class": None,
            "last_index_bars": {},
            "last_index_bar_source": {},
            "last_chain_metrics": {},
        }
    st = best.stat()
    age = max(0.0, time.time() - st.st_mtime)
    tail = ""
    last_openai = None
    last_tick = None
    last_err = None
    last_index_bars: dict = {}
    last_index_src: dict = {}
    last_chain: dict = {}
    try:
        data = best.read_bytes()
        text = data[-12000:].decode("utf-8", errors="replace")
        tail = text[-400:].replace("\n", " | ")
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("event") == "market_hours_tick":
                last_tick = obj.get("tick_index")
                if "openai_used" in obj:
                    last_openai = bool(obj.get("openai_used"))
                err = obj.get("llm_last_error_class")
                if err:
                    last_err = str(err)[:64]
                ib = obj.get("index_bars")
                if isinstance(ib, dict):
                    last_index_bars = {str(k): int(v or 0) for k, v in ib.items()}
                src = obj.get("index_bar_source")
                if isinstance(src, dict):
                    last_index_src = {str(k): str(v) for k, v in src.items()}
                cm = obj.get("chain_metrics")
                if isinstance(cm, dict):
                    last_chain = cm
                break
    except Exception:
        tail = "unreadable"
    return {
        "path": str(best),
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "age_seconds": round(age, 1),
        "tail_hint": tail[:240],
        "last_openai_used": last_openai,
        "last_tick": last_tick,
        "last_llm_error_class": last_err,
        "last_index_bars": last_index_bars,
        "last_index_bar_source": last_index_src,
        "last_chain_metrics": last_chain,
    }


def _kb_openai_stats() -> dict:
    out = {
        "sessions": 0,
        "openai_used_true": 0,
        "last_openai_used": None,
        "last_llm_error_class": None,
    }
    if not KB_PATH.exists():
        return out
    try:
        con = sqlite3.connect(str(KB_PATH))
        try:
            row = con.execute(
                "SELECT COUNT(*), COALESCE(SUM(openai_used),0) FROM sessions"
            ).fetchone()
            out["sessions"] = int(row[0] or 0)
            out["openai_used_true"] = int(row[1] or 0)
            last = con.execute(
                "SELECT openai_used, payload_json FROM sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if last is not None:
                out["last_openai_used"] = bool(last[0])
                try:
                    payload = json.loads(last[1] or "{}")
                except Exception:
                    payload = {}
                out["last_llm_error_class"] = _extract_openai_error_class(payload)
        finally:
            con.close()
    except Exception:
        pass
    return out


def _extract_openai_error_class(payload: dict) -> str | None:
    """Walk session payload for OpenAI error class names only (no secrets)."""
    found: list[str] = []

    def walk(obj: object) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str):
            s = obj
            if "OpenAI rate-limited" in s or "RateLimitError" in s:
                found.append("RateLimitError")
            elif "rate-limit cooldown" in s:
                found.append("RateLimitCooldown")
            elif "connection cooldown" in s:
                found.append("APIConnectionCooldown")
            elif "OpenAI call failed (" in s:
                start = s.rfind("(") + 1
                end = s.rfind(")")
                if start > 0 and end > start:
                    found.append(s[start:end][:64])
            elif "last_error_class=" in s:
                found.append(s.split("last_error_class=", 1)[-1].strip(" )")[:64])

    walk(payload)
    if not found:
        return None
    # Prefer transient/rate classes over stale noise.
    for pref in (
        "RateLimitError",
        "RateLimitCooldown",
        "APIConnectionCooldown",
        "APIConnectionError",
        "APITimeoutError",
    ):
        if pref in found:
            return pref
    return found[0]


def _llm_status(
    llm: dict,
    openai_used: bool | None,
    error_class: str | None,
    paper_alive: bool,
    log_age_seconds: float | None = None,
) -> str:
    """Canvas/ops label: OFF | ON | failing | retrying."""
    if not llm.get("llm_enabled"):
        return "OFF"
    if not paper_alive:
        return "failing"
    err = (error_class or "").lower()
    if "ratelimit" in err or "cooldown" in err:
        return "retrying"
    # Heartbeat stall — first LLM tick or hung HTTPS can look like this.
    if log_age_seconds is not None and log_age_seconds > 180:
        return "retrying"
    if openai_used is True and not err:
        return "ON"
    if openai_used is True and err in ("apiconnectionerror", "apitimeouterror"):
        # Partial success with transient noise — still ON but ops can see class.
        return "ON"
    if openai_used is False:
        if "ratelimit" in err or "cooldown" in err or "apiconnection" in err or "timeout" in err:
            return "retrying"
        return "failing"
    if err:
        return "failing"
    return "ON" if openai_used is True else "pending"


def _llm_flags(pids: dict) -> dict:
    flags = str(pids.get("flags") or pids.get("paper_cmd") or "")
    llm_enabled = bool(pids.get("llm_enabled"))
    if "llm_enabled" not in pids:
        llm_enabled = "--no-llm" not in flags
    live_chain = bool(pids.get("live_chain"))
    if "live_chain" not in pids:
        live_chain = "--live-chain" in flags
    return {
        "llm_enabled": llm_enabled,
        "live_chain": live_chain,
        "openai_model_hint": pids.get("openai_model_hint") or "OPENAI_MODEL",
        "flags": flags,
    }


def _clock() -> dict:
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.run(
            [str(VENV_PY), "-m", "trading_agents_india", "clock"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except Exception as exc:
        return {"error": type(exc).__name__, "reason": "clock probe failed"}
    return {"error": "clock_failed", "reason": "non-zero or empty"}


def _esc(s: object) -> str:
    return str(s).replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def _js_str(s: object) -> str:
    return json.dumps(str(s), ensure_ascii=True)


def _analysis_alive(pids: dict) -> bool:
    return _pid_alive(pids.get("analysis_loop"))


def _load_attention() -> dict:
    """Read analysis-loop attention file if present."""
    path = RECON / "paper_attention_bugs.json"
    if not path.exists():
        return {"items": [], "updated_at": None, "path": str(path)}
    try:
        obj = json.loads(path.read_text())
        return {
            "items": list(obj.get("items") or [])[:12],
            "updated_at": obj.get("updated_at_ist") or obj.get("updated_at"),
            "path": str(path),
            "level_bugs": obj.get("level_bugs") or [],
        }
    except Exception:
        return {"items": [], "updated_at": None, "path": str(path)}


def _customer_veto_reasons(*sources, limit: int = 3) -> list[str]:
    out: list[str] = []
    for src in sources:
        if not isinstance(src, list):
            continue
        for r in src:
            text = str(r or "").strip()
            if not text or text in out:
                continue
            if text.startswith(
                ("boss:", "tech:", "chain:", "bull:", "bear:", "trader:", "input_mix:", "phd_note:")
            ):
                continue
            out.append(text)
            if len(out) >= limit:
                return out[:limit]
    return out[:limit]


def _last_leans(ledger_path: Path) -> dict:
    """Newest SIGNAL leans + veto reasons + optional level fields from today's ledger."""
    out = {
        "leans": {},
        "as_of_ist": None,
        "levels": {},
        "top_veto_reasons": {},
        "updated_at": None,
    }
    if not ledger_path.exists():
        return out
    last_by_und: dict[str, dict] = {}
    try:
        with ledger_path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("event_type") != "SIGNAL":
                    continue
                und = str(obj.get("underlying") or "?")
                last_by_und[und] = obj
                out["as_of_ist"] = obj.get("as_of_ist")
    except Exception:
        return out
    for und, obj in last_by_und.items():
        lean = obj.get("lean") or obj.get("side") or "?"
        out["leans"][und] = str(lean)
        lv = {
            "entry": obj.get("entry"),
            "stop": obj.get("stop"),
            "target": obj.get("target"),
            "strike": obj.get("strike"),
        }
        if any(v is not None for v in lv.values()):
            out["levels"][und] = lv
        reasons = _customer_veto_reasons(
            obj.get("top_veto_reasons"),
            obj.get("vetoes"),
            obj.get("reasons"),
            limit=3,
        )
        if reasons:
            out["top_veto_reasons"][und] = reasons
    out["updated_at"] = out["as_of_ist"]
    return out


def _llm_cooldown_remaining() -> float:
    """Seconds left on shared LLM cooldown (P2-4 — survive respawns)."""
    path = RECON / "llm_cooldown.json"
    if not path.is_file():
        return 0.0
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0.0
    now = time.time()
    until = max(
        float(blob.get("rate_limit_until") or 0.0),
        float(blob.get("conn_until") or 0.0),
    )
    return max(0.0, until - now)


def _ist_hm() -> tuple[int, int]:
    try:
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        return now.hour, now.minute
    except Exception:
        now = datetime.now(timezone.utc)
        return now.hour, now.minute


def _write_ops_founder_digest(payload: dict) -> Path | None:
    """P1-2: digest at stop-flag or ≥15:35 IST (ops path; analysis loop also writes)."""
    stop_flag = RECON / "paper_ops_STOPPED.flag"
    hour, minute = _ist_hm()
    past_close = hour > 15 or (hour == 15 and minute >= 35)
    if not stop_flag.exists() and not past_close:
        return None
    try:
        from zoneinfo import ZoneInfo

        day = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    except Exception:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = RECON / f"FOUNDER_DIGEST_{day}.md"
    # Don't thrash: if analysis loop wrote in last 4 minutes and not stop, skip.
    if path.is_file() and not stop_flag.exists():
        age = time.time() - path.stat().st_mtime
        if age < 240:
            return path
    ledger = payload.get("ledger") or {}
    leans = payload.get("leans") or {}
    lean_map = leans.get("leans") or {}
    hold = sum(1 for v in lean_map.values() if str(v).upper() == "HOLD")
    ce = sum(1 for v in lean_map.values() if str(v).upper() == "BUY_CE")
    pe = sum(1 for v in lean_map.values() if str(v).upper() == "BUY_PE")
    sides = ledger.get("signal_sides") or {}
    if isinstance(sides, dict) and sides:
        hold = int(sides.get("HOLD") or hold)
        ce = int(sides.get("BUY_CE") or ce)
        pe = int(sides.get("BUY_PE") or pe)
    cand = int(ledger.get("candidates") or 0)
    di = int(ledger.get("di_count") or 0)
    di_pct = f"{(100.0 * di / cand):.0f}%" if cand else "n/a"
    top_p0 = (
        "P0-DI unbound STRAT evaluators (workstream C)"
        if cand and di / max(1, cand) >= 0.7
        else "none open from ops tally"
    )
    veto = leans.get("top_veto_reasons") or {}
    veto_flat: list[str] = []
    for rs in veto.values():
        for r in rs or []:
            if r not in veto_flat:
                veto_flat.append(r)
            if len(veto_flat) >= 3:
                break
        if len(veto_flat) >= 3:
            break
    lines = [
        f"# Founder digest — {day}",
        "",
        f"- Updated: {_ist_now()} · source=ops_monitor · stop_flag="
        f"{'yes' if stop_flag.exists() else 'no'}",
        "- Mode: PAPER · NO_PROMOTE · orders REFUSED · **ship=false**",
        f"- Latest leans: CE={ce} PE={pe} HOLD={hold} · day signals={ledger.get('signals', 0)}",
        f"- Candidates: {cand} · DI: {di} ({di_pct})",
        f"- LLM: status={payload.get('llm_status')} err={payload.get('llm_last_error_class')}",
        f"- Top P0: {top_p0}",
        f"- Top veto (latest): {veto_flat or 'n/a'}",
        "- Shipped: `data/recon/PROCESS_FIXES_SHIPPED_2026-09-07.md`",
        f"- EOD: `python -m agent_rag eod-recon --day {day} --offline`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    # Keep API snapshot warm even when analysis loop is down.
    latest = {
        "day": day,
        "updated_at_ist": _ist_now(),
        "as_of_ist": leans.get("as_of_ist"),
        "lean_counts": {"BUY_CE": ce, "BUY_PE": pe, "HOLD": hold},
        "signals": ledger.get("signals") or 0,
        "ce": ce,
        "pe": pe,
        "hold": hold,
        "top_veto_reasons": veto,
        "ship": False,
        "note": "Ops monitor snapshot — NO_PROMOTE; orders REFUSED",
    }
    (RECON / "paper_latest_signals.json").write_text(
        json.dumps(latest, indent=2) + "\n", encoding="utf-8"
    )
    return path


def _agent_rows(
    paper_alive: bool,
    monitor_alive: bool,
    backtest_alive: bool,
    analysis_alive: bool,
    clock: dict,
    ledger: dict,
    llm: dict,
    openai_used: bool | None,
    section_ts: str,
    log: dict | None = None,
) -> list[list[str]]:
    """Rows: agent, state, who/working, last_updated, cadence, guard."""
    paper_state = "RUNNING" if paper_alive else "DOWN"
    llm_mode = "LLM ON" if llm.get("llm_enabled") else "LLM OFF"
    chain_mode = "live-chain" if llm.get("live_chain") else "fixtures/desk"
    used = (
        "openai_used=true"
        if openai_used is True
        else ("openai_used=false" if openai_used is False else "openai_used=pending")
    )
    in_shell = bool(clock.get("in_session_shell"))
    allow = bool(clock.get("allow_directional_paper"))
    clock_note = clock.get("reason") or clock.get("error") or "unknown"
    cand = ledger.get("candidates") or 0
    sig = ledger.get("signals") or 0
    di = ledger.get("di_count") or 0
    tick_ts = (log or {}).get("mtime") or section_ts
    who_paper = "market-hours PID working" if paper_alive else "stopped"
    who_done = "tick finished → ledger" if paper_alive else "n/a"
    return [
        [
            "Market-hours runner",
            paper_state,
            who_paper,
            str(tick_ts),
            "~60s ticks",
            f"Orders refused · {used}",
        ],
        [
            "News analyst",
            paper_state if paper_alive else "IDLE",
            who_paper if paper_alive else "idle",
            section_ts,
            "Per tick",
            "Hold ticket on extreme news — not alpha",
        ],
        [
            "Sentiment analyst",
            paper_state if paper_alive else "IDLE",
            who_paper if paper_alive else "idle",
            section_ts,
            "Per tick",
            "DATA_INSUFFICIENT if unwired",
        ],
        [
            "Technical analyst",
            paper_state if paper_alive else "IDLE",
            who_paper if paper_alive else "idle",
            section_ts,
            "Per tick",
            "Confirm/kill only for 5m ST/MACD/RSI",
        ],
        [
            "Chain watcher",
            paper_state if paper_alive else "IDLE",
            chain_mode if paper_alive else "idle",
            section_ts,
            "Per tick",
            "DATA_INSUFFICIENT if chain fails",
        ],
        [
            "Bull/bear debate",
            paper_state if paper_alive else "IDLE",
            llm_mode if paper_alive else "idle",
            section_ts,
            "Per tick",
            "Handoff persisted",
        ],
        [
            "Boss research manager",
            paper_state if paper_alive else "IDLE",
            who_paper if paper_alive else "idle",
            section_ts,
            "Per tick",
            "Cannot promote",
        ],
        [
            "Trader (paper proposals)",
            paper_state if paper_alive else "IDLE",
            who_done if paper_alive else "idle",
            str(ledger.get("last_as_of_ist") or section_ts),
            "Per tick",
            "Shadow ledger only",
        ],
        [
            "Risk committee",
            paper_state if paper_alive else "IDLE",
            who_paper if paper_alive else "idle",
            section_ts,
            "Per tick",
            "Can force HOLD",
        ],
        [
            "Ops monitor",
            "RUNNING" if monitor_alive else "DOWN",
            "canvas rewriter",
            section_ts,
            "25s rewrite",
            "No orders",
        ],
        [
            "Offline PhD/backtest",
            "RUNNING" if backtest_alive else "IDLE",
            "offline rollup" if backtest_alive else "idle",
            section_ts,
            "Background",
            "UNVALIDATED / NO_PROMOTE",
        ],
        [
            "DI analysis loop",
            "RUNNING" if analysis_alive else "IDLE",
            "bug/DI scanner" if analysis_alive else "idle",
            section_ts,
            "5m cadence",
            f"{di} DATA_INSUFFICIENT · NO_PROMOTE",
        ],
        [
            "Session clock",
            "OPEN" if in_shell else "OUTSIDE",
            "IST probe",
            section_ts,
            "Each monitor pass",
            f"{'lean OK' if allow else 'HOLD/dead-band'} · {_esc(clock_note)[:80]}",
        ],
        [
            "Signal health",
            "OK" if sig > 0 or cand > 0 else "WAITING",
            who_done,
            str(ledger.get("last_as_of_ist") or section_ts),
            "Append-only",
            f"{cand} candidates / {sig} signals / {di} DI",
        ],
    ]


def _flow_rows(
    ledger: dict,
    log: dict,
    website_up: bool,
    llm: dict,
    openai_used: bool | None,
    leans: dict,
    section_ts: str,
    llm_status: str | None = None,
    llm_error_class: str | None = None,
) -> list[list[str]]:
    sides = ledger.get("signal_sides") or {}
    side_txt = ", ".join(f"{k}:{v}" for k, v in sorted(sides.items())) or "none yet"
    outcomes = ledger.get("candidate_outcomes") or {}
    out_txt = ", ".join(f"{k}:{v}" for k, v in sorted(outcomes.items(), key=lambda x: -x[1])[:4]) or "none"
    used = (
        "true" if openai_used is True else ("false" if openai_used is False else "pending")
    )
    status = llm_status or ("ON" if llm.get("llm_enabled") else "OFF")
    err = llm_error_class or "none"
    llm_txt = (
        f"LLM status={status} · enabled={llm.get('llm_enabled')} · openai_used={used} · "
        f"last_error_class={err} · live_chain={llm.get('live_chain')}"
    )
    age = log.get("age_seconds")
    age_txt = f"{age}s since mtime" if age is not None else "n/a"
    lean_map = leans.get("leans") or {}
    lean_txt = ", ".join(f"{k}:{v}" for k, v in sorted(lean_map.items())) or "n/a"
    levels = leans.get("levels") or {}
    if levels:
        level_bits = []
        for und, lv in sorted(levels.items()):
            level_bits.append(
                f"{und} e={lv.get('entry')} sl={lv.get('stop')} tp={lv.get('target')}"
            )
        level_txt = "; ".join(level_bits)
    else:
        level_txt = "none bound (entry=null on shadow — not inventing fills)"
    return [
        ["Market clock", "IST session/dead-band (real)", f"{section_ts} · recorded each probe"],
        ["Agent graph", "News → sentiment → technical → chain → debate → boss → trader → risk", f"{section_ts} · {llm_txt}"],
        [
            "Candidate audit",
            "All catalog rows preserved",
            f"{section_ts} · {ledger.get('candidates', 0)} observations · {out_txt}",
        ],
        [
            "Paper ledger",
            "Signals + shadow trades + provenance",
            (
                f"{section_ts} · {ledger.get('signals', 0)} signals / "
                f"{ledger.get('shadow', 0)} shadow "
                f"(OPEN={ledger.get('shadow_open', 0)} SKIPPED={ledger.get('shadow_skipped', 0)}) · "
                f"PAPER_TRADE={ledger.get('paper_trade', 0)} · non-HOLD signals={ledger.get('non_hold_signals', 0)} · "
                f"sides {side_txt}"
            ),
        ],
        [
            "Paper trade reference",
            "SHADOW_OPEN = directional paper ref; SKIPPED/HOLD = audit only (not a fill)",
            (
                f"{section_ts} · OPEN={ledger.get('shadow_open', 0)} · "
                f"SKIPPED={ledger.get('shadow_skipped', 0)} · "
                f"filled PAPER_TRADE rows={ledger.get('paper_trade', 0)} (always 0 — no invent fills)"
            ),
        ],
        [
            "Last signal lean",
            lean_txt,
            f"{leans.get('as_of_ist') or section_ts} · levels: {level_txt}",
        ],
        ["Customer signal", "CE / PE / HOLD with bounded confidence", f"{section_ts} · No win-rate claim"],
        [
            "Log capture",
            Path(log["path"]).name if log.get("path") else "missing",
            f"{section_ts} · {log.get('bytes', 0)} bytes · {age_txt} · tick={log.get('last_tick')}",
        ],
        ["Website", "Vite :5173", f"{section_ts} · {'UP' if website_up else 'DOWN'}"],
        [
            "Last ledger event",
            str(ledger.get("last_event_type") or "n/a"),
            str(ledger.get("last_as_of_ist") or "n/a"),
        ],
    ]


def _tuning_rows(
    paper_alive: bool,
    ledger: dict,
    log: dict,
    clock: dict,
    llm: dict,
    openai_used: bool | None,
    website_up: bool,
    attention: dict | None = None,
    llm_status: str | None = None,
    llm_error_class: str | None = None,
) -> list[list[str]]:
    """Actionable founder attention only — DI/fixture noise goes to parked."""
    rows: list[list[str]] = []
    stop_flag = (RECON / "paper_ops_STOPPED.flag").exists()
    att = attention or {}
    for item in att.get("items") or []:
        if isinstance(item, dict):
            why = str(item.get("why") or "")
            if _is_parked_attention_why(why):
                continue
            rows.append(
                [
                    str(item.get("surface") or "Analysis"),
                    str(item.get("action") or "Review"),
                    why[:160],
                ]
            )
        else:
            if _is_parked_attention_why(str(item)):
                continue
            rows.append(["Analysis attention", "Review", str(item)[:160]])
    if stop_flag:
        rows.append(
            [
                "Stop flag",
                "Do not restart",
                "paper_ops_STOPPED.flag present — wait for founder before npm/paper",
            ]
        )
    elif not paper_alive:
        rows.append(["Market-hours runner", "Restart", "Process not alive — ops monitor may restart once"])
    if not stop_flag and not website_up:
        rows.append(["Website :5173", "Start Vite", "Customer mock desk not responding"])
    status = (llm_status or "").lower()
    if not stop_flag and status == "retrying":
        rows.append(
            [
                "LLM path",
                "Backoff then retry",
                f"status=retrying · last_error_class={llm_error_class or 'RateLimitCooldown'} — will hit OpenAI again after cooldown",
            ]
        )
    elif not stop_flag and (
        status == "failing"
        or (llm.get("llm_enabled") and openai_used is False and paper_alive)
    ):
        rows.append(
            [
                "LLM path",
                "Retry / restart",
                f"status=failing · openai_used=false · last_error_class={llm_error_class or 'unknown'}",
            ]
        )
    if not stop_flag and llm.get("llm_enabled") is False:
        rows.append(["LLM", "Re-enable", "Running without LLM — founder wants production-like LLM ON"])
    if not stop_flag and not llm.get("live_chain") and paper_alive:
        rows.append(
            [
                "live-chain",
                "Check DHAN_*",
                "Daemon started without live-chain — chain may be fixtures only",
            ]
        )
    if log.get("bytes", 0) == 0 and paper_alive:
        rows.append(["Stdout log", "Buffering", "Log still empty — confirm PYTHONUNBUFFERED=1"])
    age = log.get("age_seconds")
    if paper_alive and age is not None and age > 180:
        rows.append(
            [
                "Heartbeat latency",
                "Investigate stall",
                f"Log mtime age {age}s — tick may be blocked on LLM/Dhan",
            ]
        )
    if not clock.get("in_session_shell") and paper_alive:
        rows.append(
            [
                "Session shell",
                "Expect HOLD",
                "Outside 09:00–15:30 IST — directional paper suppressed; loop continues for capture",
            ]
        )
    _ = ledger
    if not rows:
        rows.append(["None urgent", "Observe", "Signals appending; keep PAPER / NO_PROMOTE / orders refused"])
    return rows[:12]


def _is_parked_attention_why(why: str) -> bool:
    w = (why or "").lower()
    return (
        "levels_non_numeric" in w
        or "di ratio" in w
        or "data_insufficient" in w
        or "tune data path" in w
        or "unbound strat" in w
    )


def _parked_tuning_rows(attention: dict | None, ledger: dict) -> list[list[str]]:
    """Fixture LEVELS + DI restates — collapsed on canvas (unplugged from primary)."""
    rows: list[list[str]] = []
    att = attention or {}
    for item in att.get("level_bugs") or []:
        rows.append(
            [
                str(item.get("surface") or "Levels"),
                "PARKED",
                str(item.get("why") or item.get("bug") or "LEVELS_NON_NUMERIC")[:160],
            ]
        )
    for item in att.get("items") or []:
        if isinstance(item, dict):
            why = str(item.get("why") or "")
            if _is_parked_attention_why(why):
                rows.append(
                    [
                        str(item.get("surface") or "Analysis"),
                        "PARKED on canvas",
                        why[:160],
                    ]
                )
        elif _is_parked_attention_why(str(item)):
            rows.append(["Analysis attention", "PARKED on canvas", str(item)[:160]])
    di = int(ledger.get("di_count") or 0)
    cand = int(ledger.get("candidates") or 0)
    if cand and di >= max(1, int(0.7 * cand)):
        rows.append(
            [
                "DI ratio restatement",
                "PARKED on canvas",
                f"DI {di}/{cand} — see DI honesty card; not a per-cycle founder action",
            ]
        )
    return rows[:12]


def _agent_detail_rows(agents: list[list[str]]) -> list[list[str]]:
    """Slim roster for collapsed canvas section (drop persona DI chatter)."""
    keep = {
        "Market-hours runner",
        "Trader (paper proposals)",
        "Risk committee",
        "Ops monitor",
        "DI analysis loop",
        "Session clock",
        "Signal health",
        "Offline PhD/backtest",
    }
    out: list[list[str]] = []
    for r in agents:
        if not r:
            continue
        name = str(r[0])
        if name not in keep:
            continue
        # agent, state, who, guard (drop cadence)
        out.append([name, str(r[1]), str(r[2]), str(r[5] if len(r) > 5 else "")])
    return out


def _render_canvas(payload: dict) -> str:
    """Founder-ops canvas: veto + LLM + digests primary; DI/agents/flow collapsed."""
    agents = payload["agent_rows"]
    tuning = payload["tuning_rows"]
    parked = payload.get("parked_tuning_rows") or []
    di_rows = payload.get("di_why_rows") or []
    veto_rows = payload.get("veto_rows") or []
    paper_alive = payload["paper_alive"]
    website_up = payload["website_up"]
    api_up = payload.get("api_up", True)
    ledger = payload["ledger"]
    clock = payload["clock"]
    llm = payload["llm"]
    openai_used = payload.get("openai_used")
    llm_status = payload.get("llm_status") or ("ON" if llm.get("llm_enabled") else "OFF")
    llm_error_class = payload.get("llm_last_error_class") or "none"
    log_meta = payload.get("log") or {}
    index_bars = log_meta.get("last_index_bars") or {}
    index_src = log_meta.get("last_index_bar_source") or {}
    nifty_bars = int(index_bars.get("NIFTY") or 0)
    index_src_one = str(index_src.get("NIFTY") or next(iter(index_src.values()), "unavailable"))
    index_tone = "success" if nifty_bars >= 80 and "dhan" in index_src_one else "warning"
    chain_meta = log_meta.get("last_chain_metrics") or {}
    nifty_chain = chain_meta.get("NIFTY") if isinstance(chain_meta.get("NIFTY"), dict) else {}
    nifty_ltp = nifty_chain.get("option_ltp")
    nifty_spot = nifty_chain.get("spot")
    chain_ltp_txt = (
        f"LTP {nifty_ltp} · spot {nifty_spot}"
        if nifty_ltp not in (None, "")
        else "LTP n/a"
    )
    chain_ltp_tone = "success" if nifty_ltp not in (None, "") else "warning"
    sections = payload.get("section_ts") or {}
    overall = payload["updated_at"]
    attention = payload.get("attention") or {}
    day = overall.split(" ")[0] if overall else ""

    paper_tone = "success" if paper_alive else "danger"
    web_tone = "success" if website_up else "danger"
    api_tone = "success" if api_up else "danger"
    llm_status_l = str(llm_status).lower()
    if llm_status_l == "on":
        llm_tone = "success"
    elif llm_status_l == "retrying":
        llm_tone = "warning"
    elif llm_status_l in ("failing", "off"):
        llm_tone = "danger" if llm_status_l == "failing" else "warning"
    else:
        llm_tone = "info"
    used_txt = (
        "true" if openai_used is True else ("false" if openai_used is False else "pending")
    )
    used_tone = (
        "success"
        if openai_used is True
        else ("warning" if openai_used is False else "info")
    )
    err_tone = (
        "success"
        if (not llm_error_class or llm_error_class == "none") and openai_used is True
        else ("warning" if llm_status_l == "retrying" else "danger" if llm_status_l == "failing" else "info")
    )
    shell_tone = "success" if clock.get("in_session_shell") else "info"
    sides = ledger.get("signal_sides") or {}
    hold_n, ce_n, pe_n = _side_counts(sides)
    digest_path = f"data/recon/FOUNDER_DIGEST_{day}.md" if day else "data/recon/FOUNDER_DIGEST_*.md"
    queue_path = f"data/recon/ATTENTION_QUEUE_{day}.md" if day else "data/recon/ATTENTION_QUEUE_*.md"
    att_path = str(attention.get("path") or queue_path)

    agent_detail = _agent_detail_rows(agents)
    agent_tones = [_state_tone(r[1] if len(r) > 1 else "") for r in agent_detail]
    di_tones = []
    for r in di_rows:
        head = str(r[0] if r else "").lower()
        if "promote" in head:
            di_tones.append("danger")
        elif "vetoed" in head:
            di_tones.append("info")
        else:
            di_tones.append("warning")
    veto_tones = ["warning"] * len(veto_rows)
    tuning_tones = ["warning"] * len(tuning)
    parked_tones = ["info"] * len(parked)

    def rows_ts(rows: list[list[str]]) -> str:
        parts = []
        for r in rows:
            parts.append("[" + ", ".join(_js_str(c) for c in r) + "]")
        return ",\n  ".join(parts) if parts else ""

    def tones_ts(tones: list[str]) -> str:
        return ", ".join(_js_str(t) for t in tones) if tones else ""

    sealed = (not paper_alive) and (not clock.get("in_session_shell"))
    status_pill = "FINAL / STOPPED" if sealed else ("RUNNING" if paper_alive else "STOPPED")

    return f"""import {{
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
}} from "cursor/canvas";

/** Unplug policy: teams/00_orchestrator/docs/PAPER_OPS_CANVAS.md */

const vetoRows = [
  {rows_ts(veto_rows)}
];
const vetoTones = [{tones_ts(veto_tones)}];

const diTopRows = [
  {rows_ts(di_rows)}
];
const diTopTones = [{tones_ts(di_tones)}];

const tuningRows = [
  {rows_ts(tuning)}
];
const tuningTones = [{tones_ts(tuning_tones)}];

const agentDetailRows = [
  {rows_ts(agent_detail)}
];
const agentDetailTones = [{tones_ts(agent_tones)}];

const parkedRows = [
  {rows_ts(parked)}
];
const parkedTones = [{tones_ts(parked_tones)}];

export default function PaperOperationsMonitor() {{
  return (
    <Stack gap={{20}} style={{{{ padding: 24, maxWidth: 960, margin: "0 auto" }}}}>
      <Stack gap={{8}}>
        <H1>Paper operations monitor</H1>
        <Text tone="secondary">
          {_esc(overall)} · supervised PAPER only · orders REFUSED
        </Text>
        <Row gap={{8}} wrap>
          <Pill active size="sm">{_esc(status_pill)}</Pill>
          <Pill active size="sm">promote=false</Pill>
          <Pill active size="sm">orders REFUSED</Pill>
          <Pill active size="sm">NO_PROMOTE</Pill>
        </Row>
      </Stack>

      <Grid columns={{4}} gap={{12}}>
        <Stat label="Paper loop" value={_js_str("RUNNING" if paper_alive else "STOPPED")} tone="{paper_tone}" />
        <Stat label="Session" value={_js_str("OPEN" if clock.get("in_session_shell") else "CLOSED")} tone="{shell_tone}" />
        <Stat label="Signals / shadow" value={_js_str(str(ledger.get("signals", 0)) + " / " + str(ledger.get("shadow", 0)))} />
        <Stat label="promote" value="false" tone="danger" />
      </Grid>

      <Grid columns={{4}} gap={{12}}>
        <Stat label="HOLD / CE / PE" value={_js_str(f"{hold_n} / {ce_n} / {pe_n}")} tone="info" />
        <Stat label="Shadow OPEN / SKIPPED" value={_js_str(str(ledger.get("shadow_open", 0)) + " / " + str(ledger.get("shadow_skipped", 0)))} tone="info" />
        <Stat label="PAPER fills" value={_js_str(str(ledger.get("paper_trade", 0)))} tone="info" />
        <Stat label="Non-HOLD signals" value={_js_str(str(ledger.get("non_hold_signals", 0)))} tone={_js_str("success" if int(ledger.get("non_hold_signals") or 0) else "info")} />
      </Grid>

      <Grid columns={{4}} gap={{12}}>
        <Stat label="LLM status" value={_js_str(str(llm_status))} tone="{llm_tone}" />
        <Stat label="openai_used" value={_js_str(used_txt)} tone="{used_tone}" />
        <Stat label="LLM last error" value={_js_str(str(llm_error_class)[:40])} tone="{err_tone}" />
        <Stat label="API / Vite" value={_js_str(("UP" if api_up else "DOWN") + " / " + ("UP" if website_up else "DOWN"))} tone={_js_str("danger" if (not api_up or not website_up) else "success")} />
      </Grid>

      <Grid columns={{4}} gap={{12}}>
        <Stat label="INDEX 1m NIFTY" value={_js_str(str(nifty_bars))} tone="{index_tone}" />
        <Stat label="INDEX 1m BN" value={_js_str(str(int(index_bars.get("BANKNIFTY") or 0)))} tone="{index_tone}" />
        <Stat label="INDEX 1m SENSEX" value={_js_str(str(int(index_bars.get("SENSEX") or 0)))} tone="{index_tone}" />
        <Stat label="INDEX source" value={_js_str(index_src_one[:28])} tone="{index_tone}" />
      </Grid>
      <Grid columns={{2}} gap={{12}}>
        <Stat label="NIFTY ATM premium" value={_js_str(chain_ltp_txt)} tone="{chain_ltp_tone}" />
        <Stat label="News API" value="OFF" tone="info" />
      </Grid>

      <Callout tone="info" title="Ops guardrail">
        PAPER only · NO_PROMOTE · orders REFUSED. Missing data = DATA_INSUFFICIENT or HOLD.
        Gate is not RESEARCH_READY_FOR_PROGRAMMING. Confidence is not a win rate.
        DI mass is collapsed below — unbound STRAT-001..014 stay KEEP_ALL.
      </Callout>

      <H2>Top veto reasons (customer ticket) · {_esc(sections.get("leans") or overall)}</H2>
      <Text tone="secondary" size="small">
        Why CE/PE stayed off — policy/veto stack, not UI death.
      </Text>
      <Table
        headers={{["Reason", "Count / state", "Note"]}}
        rows={{vetoRows}}
        rowTone={{vetoTones}}
        striped
        stickyHeader
      />

      <H2>Attention · {_esc(sections.get("attention") or overall)}</H2>
      <Table
        headers={{["Surface", "Action", "Why"]}}
        rows={{tuningRows}}
        rowTone={{tuningTones}}
        striped
      />
      <Stack gap={{6}}>
        <Text>Digest: <Code>{_esc(digest_path)}</Code></Text>
        <Text>Attention queue: <Code>{_esc(att_path)}</Code></Text>
        <Text tone="secondary" size="small">
          Analysis loop scans; it does not ship. See PROCESS_FIXES_SHIPPED_*.md for real ships.
        </Text>
      </Stack>

      <Card collapsible defaultOpen={{false}}>
        <CardHeader trailing={{<Pill size="sm" active>honesty · not delete</Pill>}}>
          DI honesty (grouped) · unbound STRATs · {_esc(sections.get("di_why") or overall)}
        </CardHeader>
        <CardBody>
          <Stack gap={{12}}>
            <Text tone="secondary" size="small">
              DATA_INSUFFICIENT mass is almost entirely unbound STRAT-001–014 evaluators.
              KEEP_ALL — DI ≠ catalog kill. Collapsed so DI does not drown FINAL / veto / LLM.
            </Text>
            <Table
              headers={{["Cause", "Count / state", "Why"]}}
              rows={{diTopRows}}
              rowTone={{diTopTones}}
              striped
            />
          </Stack>
        </CardBody>
      </Card>

      <Divider />
      <Text tone="tertiary" size="small">
        Unplugged from primary view — see teams/00_orchestrator/docs/PAPER_OPS_CANVAS.md
      </Text>

      <Card collapsible defaultOpen={{false}}>
        <CardHeader>Agent roster (detail · unplugged)</CardHeader>
        <CardBody>
          <Table
            headers={{["Agent/process", "State", "Who", "Guard"]}}
            rows={{agentDetailRows}}
            rowTone={{agentDetailTones}}
            striped
          />
        </CardBody>
      </Card>

      <Card collapsible defaultOpen={{false}}>
        <CardHeader>Parked fixture / DI noise (unplugged)</CardHeader>
        <CardBody>
          <Table
            headers={{["Surface", "Status", "Why parked on canvas"]}}
            rows={{parkedRows}}
            rowTone={{parkedTones}}
            striped
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader trailing={{<Pill size="sm" active>promote=false</Pill>}}>
          Operational notes · {_esc(overall)}
        </CardHeader>
        <CardBody>
          <Stack gap={{8}}>
            <Text>
              Paper PID {payload.get("paper_pid") or "n/a"} · monitor PID{" "}
              {payload.get("monitor_pid") or "n/a"} · analysis PID{" "}
              {payload.get("analysis_pid") or "n/a"} · API {_esc(str(payload.get("api_pid") or "n/a"))} ·
              Vite {_esc(str(payload.get("vite_pid") or "n/a"))}.
            </Text>
            <Text tone="secondary" size="small">
              Ledger: {_esc(ledger.get("path"))}. Last event: {_esc(ledger.get("last_event_type"))} @{" "}
              {_esc(ledger.get("last_as_of_ist"))}. No auto-tune / promote / orders.
            </Text>
          </Stack>
        </CardBody>
      </Card>
    </Stack>
  );
}}
"""



def _build_paper_cmd(live_chain: bool, tick_seconds: int = 90) -> list[str]:
    cmd = [
        str(VENV_PY),
        "-u",
        "-m",
        "trading_agents_india",
        "market-hours",
        "--mode",
        "PAPER",
        "--use-llm",
        "--tick-seconds",
        str(max(90, int(tick_seconds))),
        "--max-ticks",
        "900",
        "--no-gather-news",
    ]
    if live_chain:
        cmd.append("--live-chain")
    return cmd


def _maybe_restart_paper(paper_alive: bool, pids: dict) -> dict | None:
    """Restart paper market-hours at most once (PAPER / LLM soft-on / live-chain).

    P2-4: do not restart into an active shared LLM cooldown (avoids re-burst).
    Tick floor 90s when LLM on (P0-4).
    """
    if paper_alive:
        return None
    if RESTART_FLAG.exists():
        return {"restarted": False, "reason": "restart_already_used"}
    remaining = _llm_cooldown_remaining()
    if remaining > 5.0:
        return {
            "restarted": False,
            "reason": f"llm_cooldown_{remaining:.0f}s",
            "cooldown_remaining_s": round(remaining, 1),
        }
    log_path = RECON / "paper_market_hours_ops.log"
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    # Explicit shared cooldown path so respawn inherits strikes.
    env.setdefault(
        "TAI_LLM_COOLDOWN_PATH",
        str(RECON / "llm_cooldown.json"),
    )
    env.setdefault("NEWS_VETO_ENABLED", "false")
    llm = _llm_flags(pids)
    live_chain = bool(llm.get("live_chain"))
    # P0-4: ≥90s when LLM (daemon previously used 60).
    cmd = _build_paper_cmd(live_chain=live_chain, tick_seconds=90)
    try:
        with log_path.open("a") as fh:
            fh.write(f"\n# monitor restart {_ist_now()} cmd={' '.join(cmd)}\n")
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=fh,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
        pids = _load_pids()
        pids["paper_market_hours"] = proc.pid
        pids["paper_log"] = str(log_path)
        pids["paper_cmd"] = " ".join(cmd)
        pids["llm_enabled"] = True
        pids["live_chain"] = live_chain
        pids["paper_restarted_at"] = _ist_now()
        _save_pids(pids)
        RESTART_FLAG.write_text(_ist_now() + "\n")
        return {"restarted": True, "pid": proc.pid}
    except Exception as exc:
        return {"restarted": False, "reason": f"{type(exc).__name__}: {exc}"}


def _di_why_summary(ledger: dict) -> str:
    di = int(ledger.get("di_count") or 0)
    cand = int(ledger.get("candidates") or 0)
    unbound = int(ledger.get("di_unbound_evaluator") or 0)
    hold_n = int(ledger.get("di_hold_lean") or 0)
    buckets = ledger.get("di_buckets") or {}
    top = sorted(buckets.items(), key=lambda x: -x[1])[:3]
    top_txt = "; ".join(f"{b}×{c}" for b, c in top) if top else "no bucket tallies yet"
    ratio = f"{(100.0 * di / cand):.0f}%" if cand else "n/a"
    return (
        f"DI={di}/{cand} ({ratio}). Unbound STRAT evaluators on {unbound} DI rows. "
        f"HOLD lean on {hold_n} DI rows. Top buckets: {top_txt}. "
        "Keep ALL STRAT-001–014 in BACKTEST_BOOK — DI is honesty, not a catalog delete. "
        "Orders refused · NO_PROMOTE."
    )


def _listener_pid(port: int) -> int | None:
    try:
        proc = subprocess.run(
            ["lsof", "-tiTCP:%d" % port, "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        line = (proc.stdout or "").strip().splitlines()
        if line:
            return int(line[0].strip())
    except Exception:
        return None
    return None


def collect(monitor_pid: int | None = None, allow_restart: bool = False) -> dict:
    pids = _load_pids()
    paper_pid = pids.get("paper_market_hours")
    backtest_pid = pids.get("offline_backtest")
    analysis_pid = pids.get("analysis_loop")
    mon_pid = monitor_pid or pids.get("ops_monitor") or os.getpid()
    paper_alive = _pid_alive(paper_pid)
    restart_info = None
    if allow_restart and not paper_alive:
        restart_info = _maybe_restart_paper(False, pids)
        if restart_info and restart_info.get("restarted"):
            paper_pid = restart_info.get("pid")
            paper_alive = _pid_alive(paper_pid)
            pids = _load_pids()
    backtest_alive = _pid_alive(backtest_pid)
    analysis_alive = _analysis_alive(pids)
    monitor_alive = True
    website_up = _port_up(5173)
    api_up = _port_up(8000)
    api_pid = _listener_pid(8000)
    vite_pid = _listener_pid(5173)
    ledger_path = _ledger_day_path()
    ledger = _count_ledger(ledger_path)
    log = _log_meta()
    clock = _clock()
    llm = _llm_flags(pids)
    kb = _kb_openai_stats()
    openai_used = log.get("last_openai_used")
    if openai_used is None:
        openai_used = kb.get("last_openai_used")
    llm_error_class = log.get("last_llm_error_class") or kb.get("last_llm_error_class")
    llm_status = _llm_status(
        llm,
        openai_used,
        llm_error_class,
        paper_alive,
        log_age_seconds=log.get("age_seconds"),
    )
    attention = _load_attention()
    leans = _last_leans(ledger_path)
    now = _ist_now()
    section_ts = {
        "overall": now,
        "agents": now,
        "flow": now,
        "di_why": now,
        "attention": attention.get("updated_at") or now,
        "leans": leans.get("updated_at") or ledger.get("last_as_of_ist") or now,
    }
    di_why_rows = _di_why_rows(
        ledger, clock, llm, website_up, api_up, leans, section_ts["di_why"]
    )
    di_why_summary = _di_why_summary(ledger)
    veto_rows = _veto_rows(ledger, clock, section_ts["leans"])
    tuning_rows = _tuning_rows(
        paper_alive,
        ledger,
        log,
        clock,
        llm,
        openai_used,
        website_up,
        attention,
        llm_status=llm_status,
        llm_error_class=llm_error_class,
    )
    parked_tuning_rows = _parked_tuning_rows(attention, ledger)
    if not parked_tuning_rows:
        parked_tuning_rows = [
            ["None parked", "—", "No fixture LEVELS / DI restates this pass"]
        ]

    data_mode = (
        f"Production-like PAPER: LLM={'ON' if llm.get('llm_enabled') else 'OFF'}, "
        f"status={llm_status}, live_chain={bool(llm.get('live_chain'))}, real IST clock, no --simulate. "
        f"INDEX 1m bars={log.get('last_index_bars') or {}} src={log.get('last_index_bar_source') or {}}. "
        "News API off (--no-gather-news). Orders always refused. "
        "Rate-limit → temporary rule fallback then retry LLM. "
        "Transient connection errors → in-call backoff retry."
    )
    payload = {
        "updated_at": now,
        "section_ts": section_ts,
        "paper_alive": paper_alive,
        "website_up": website_up,
        "api_up": api_up,
        "api_pid": api_pid,
        "vite_pid": vite_pid,
        "paper_pid": paper_pid,
        "monitor_pid": mon_pid,
        "backtest_pid": backtest_pid,
        "analysis_pid": analysis_pid,
        "backtest_alive": backtest_alive,
        "analysis_alive": analysis_alive,
        "ledger": ledger,
        "log": log,
        "clock": clock,
        "llm": llm,
        "kb": kb,
        "openai_used": openai_used,
        "llm_status": llm_status,
        "llm_last_error_class": llm_error_class,
        "data_mode": data_mode,
        "restart": restart_info,
        "attention": attention,
        "leans": leans,
        "di_why_rows": di_why_rows,
        "di_why_summary": di_why_summary,
        "veto_rows": veto_rows,
        "agent_rows": _agent_rows(
            paper_alive,
            monitor_alive,
            backtest_alive,
            analysis_alive,
            clock,
            ledger,
            llm,
            openai_used,
            section_ts["agents"],
            log,
        ),
        "flow_rows": _flow_rows(
            ledger, log, website_up, llm, openai_used, leans, section_ts["flow"],
            llm_status=llm_status,
            llm_error_class=llm_error_class,
        ),
        "tuning_rows": tuning_rows,
        "parked_tuning_rows": parked_tuning_rows,
    }
    return payload


def write_status(payload: dict) -> None:
    leans = payload.get("leans") or {}
    slim = {
        "updated_at": payload["updated_at"],
        "paper_alive": payload["paper_alive"],
        "website_up": payload["website_up"],
        "paper_pid": payload.get("paper_pid"),
        "monitor_pid": payload.get("monitor_pid"),
        "backtest_pid": payload.get("backtest_pid"),
        "analysis_pid": payload.get("analysis_pid"),
        "signals": payload["ledger"].get("signals"),
        "shadow": payload["ledger"].get("shadow"),
        "shadow_open": payload["ledger"].get("shadow_open"),
        "shadow_skipped": payload["ledger"].get("shadow_skipped"),
        "paper_trade": payload["ledger"].get("paper_trade"),
        "non_hold_signals": payload["ledger"].get("non_hold_signals"),
        "candidates": payload["ledger"].get("candidates"),
        "di_count": payload["ledger"].get("di_count"),
        "di_unbound_evaluator": payload["ledger"].get("di_unbound_evaluator"),
        "di_hold_lean": payload["ledger"].get("di_hold_lean"),
        "di_why_summary": payload.get("di_why_summary"),
        "llm_enabled": payload["llm"].get("llm_enabled"),
        "live_chain": payload["llm"].get("live_chain"),
        "openai_used": payload.get("openai_used"),
        "llm_status": payload.get("llm_status"),
        "llm_last_error_class": payload.get("llm_last_error_class"),
        "backtest_alive": payload.get("backtest_alive"),
        "analysis_alive": payload.get("analysis_alive"),
        "api_up": payload.get("api_up"),
        "api_pid": payload.get("api_pid"),
        "vite_pid": payload.get("vite_pid"),
        "log_bytes": payload["log"].get("bytes"),
        "log_age_seconds": payload["log"].get("age_seconds"),
        "in_session_shell": payload["clock"].get("in_session_shell"),
        "allow_directional_paper": payload["clock"].get("allow_directional_paper"),
        "restart": payload.get("restart"),
        "leans": leans.get("leans") or {},
        "top_veto_reasons": leans.get("top_veto_reasons") or {},
        "founder_digest": payload.get("founder_digest"),
        "index_bars": (payload.get("log") or {}).get("last_index_bars") or {},
        "index_bar_source": (payload.get("log") or {}).get("last_index_bar_source") or {},
        "chain_metrics": (payload.get("log") or {}).get("last_chain_metrics") or {},
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "mode": "PAPER",
        "promote": "NO_PROMOTE",
        "orders": "REFUSED",
    }
    STATUS_FILE.write_text(json.dumps(slim, indent=2) + "\n")


def rewrite_once(monitor_pid: int | None = None, allow_restart: bool = False) -> dict:
    payload = collect(monitor_pid=monitor_pid, allow_restart=allow_restart)
    CANVAS.parent.mkdir(parents=True, exist_ok=True)
    CANVAS.write_text(_render_canvas(payload))
    # P1-2: founder digest at stop / ≥15:35 IST (does not rewrite canvas content).
    digest = _write_ops_founder_digest(payload)
    if digest:
        payload["founder_digest"] = str(digest)
    write_status(payload)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="PAPER ops canvas monitor")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=25)
    ap.add_argument("--max-loops", type=int, default=0, help="0 = forever")
    ap.add_argument("--allow-restart", action="store_true", help="Restart paper once if down")
    args = ap.parse_args()
    RECON.mkdir(parents=True, exist_ok=True)
    pids = _load_pids()
    pids["ops_monitor"] = os.getpid()
    _save_pids(pids)
    loops = 0
    while True:
        try:
            payload = rewrite_once(monitor_pid=os.getpid(), allow_restart=args.allow_restart)
            msg = (
                f"{payload['updated_at']} paper={payload['paper_alive']} "
                f"llm={payload['llm'].get('llm_enabled')} "
                f"llm_status={payload.get('llm_status')} "
                f"openai_used={payload.get('openai_used')} "
                f"llm_err={payload.get('llm_last_error_class')} "
                f"live_chain={payload['llm'].get('live_chain')} "
                f"sig={payload['ledger'].get('signals')} "
                f"shadow={payload['ledger'].get('shadow')} "
                f"cand={payload['ledger'].get('candidates')} "
                f"di={payload['ledger'].get('di_count')} "
                f"log_bytes={payload['log'].get('bytes')} "
                f"age={payload['log'].get('age_seconds')} "
                f"restart={payload.get('restart')}\n"
            )
            with MONITOR_LOG.open("a") as fh:
                fh.write(msg)
        except Exception as exc:
            with MONITOR_LOG.open("a") as fh:
                fh.write(f"{_ist_now()} ERROR {type(exc).__name__}: {exc}\n")
        loops += 1
        if args.once or (args.max_loops and loops >= args.max_loops):
            break
        time.sleep(max(5, int(args.interval)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
