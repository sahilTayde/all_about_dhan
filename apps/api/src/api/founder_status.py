"""Founder /pm payload from paper-ops files. Never include secrets."""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_RECON = _REPO_ROOT / "data" / "recon"
_STATUS = _RECON / "paper_ops_monitor_status.json"
_PIDS = _RECON / "paper_ops_pids.json"
_STOP = _RECON / "paper_ops_STOPPED.flag"

_SECRET_KEYS = frozenset(
    {
        "access_token",
        "accessToken",
        "dhan_access_token",
        "openai_api_key",
        "gemini_key",
        "gemini_api_key",
        "youtube_api_key",
        "token",
        "secret",
        "password",
        "authorization",
    }
)


def _ist_now() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _port_up(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def _pid_alive(pid: Any) -> bool:
    try:
        n = int(pid)
    except (TypeError, ValueError):
        return False
    if n <= 0:
        return False
    try:
        os.kill(n, 0)
        return True
    except OSError:
        return False


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return blob if isinstance(blob, dict) else {}


def _scrub(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = str(k)
            if key.lower() in _SECRET_KEYS or "token" in key.lower() or "secret" in key.lower():
                continue
            out[key] = _scrub(v)
        return out
    if isinstance(obj, list):
        return [_scrub(x) for x in obj]
    return obj


def _tone(*, up: bool, wanted: bool, stopped: bool = False) -> str:
    if stopped:
        return "grey"
    if not wanted:
        return "grey"
    return "green" if up else "red"


def build_founder_status() -> dict[str, Any]:
    status = _scrub(_load_json(_STATUS))
    pids = _scrub(_load_json(_PIDS))
    stopped = _STOP.is_file()
    paper_pid = pids.get("paper_market_hours") or status.get("paper_pid")
    mon_pid = pids.get("ops_monitor") or status.get("monitor_pid")
    analysis_pid = pids.get("analysis_loop") or status.get("analysis_pid")
    paper_alive = _pid_alive(paper_pid)
    mon_alive = _pid_alive(mon_pid)
    analysis_alive = _pid_alive(analysis_pid)
    api_up = _port_up(8000)
    vite_up = _port_up(5173)
    live_chain = bool(pids.get("live_chain") or status.get("live_chain"))
    llm_on = bool(pids.get("llm_enabled") or status.get("llm_enabled"))

    agents = [
        {
            "id": "paper-loop",
            "name": "Paper market-hours",
            "task": "REST --live-chain every ~90s: option chain + INDEX 1m → MIX paper tickets. No orders.",
            "alive": paper_alive,
            "pid": paper_pid if paper_alive else None,
            "tone": _tone(up=paper_alive, wanted=not stopped, stopped=stopped),
            "detail": "STOPPED flag" if stopped else ("running" if paper_alive else "not running"),
        },
        {
            "id": "ops-monitor",
            "name": "Ops monitor",
            "task": "Rewrite Cursor canvas + paper_ops_monitor_status.json (~25s).",
            "alive": mon_alive,
            "pid": mon_pid if mon_alive else None,
            "tone": _tone(up=mon_alive, wanted=True),
            "detail": "writing status JSON" if mon_alive else "monitor down — /pm will go stale",
        },
        {
            "id": "analysis-loop",
            "name": "Offline analysis loop",
            "task": "Background DI/label rollup. NO_PROMOTE.",
            "alive": analysis_alive,
            "pid": analysis_pid if analysis_alive else None,
            "tone": "green" if analysis_alive else "amber",
            "detail": "optional; paper tickets do not depend on this",
        },
        {
            "id": "llm-agents",
            "name": "Paper LLM agents",
            "task": "Boss/debate path inside each tick when OPENAI key present.",
            "alive": paper_alive and llm_on,
            "pid": None,
            "tone": "green" if (paper_alive and llm_on) else ("amber" if paper_alive else "grey"),
            "detail": status.get("llm_status") or ("ON" if llm_on else "off / rules-only"),
        },
    ]

    services = [
        {
            "id": "api",
            "name": "FastAPI :8000",
            "tone": "green" if api_up else "red",
            "detail": "health + /founder/status" if api_up else "down",
        },
        {
            "id": "vite",
            "name": "Founder / customer site :5173",
            "tone": "green" if vite_up else "red",
            "detail": "/pm this page" if vite_up else "Vite down",
        },
        {
            "id": "dhan-chain",
            "name": "Dhan live-chain",
            "tone": "green" if live_chain and paper_alive else ("amber" if live_chain else "red"),
            "detail": "REST optionchain + INDEX 1m" if live_chain else "credentials missing — fixtures",
        },
    ]

    issues: list[str] = []
    if stopped:
        issues.append("paper_ops_STOPPED.flag is set — loop should not run")
    if not paper_alive and not stopped:
        issues.append("Paper market-hours process is not running")
    if not mon_alive:
        issues.append("Ops monitor is not running — agent board will go stale")
    if not api_up:
        issues.append("API :8000 is down")
    if not vite_up:
        issues.append("Website :5173 is down")
    err = status.get("llm_last_error_class")
    if err:
        issues.append(f"LLM last error class: {err}")

    next_action = "Watch paper leans — no promote, no orders."
    if issues:
        next_action = issues[0]

    return {
        "ok": not issues,
        "as_of": _ist_now(),
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "promote": False,
        "orders": "REFUSED",
        "mode": pids.get("mode") or "PAPER",
        "next_action": next_action,
        "stopped": stopped,
        "issues": issues,
        "agents": agents,
        "services": services,
        "leans": status.get("leans") or {},
        "chain_metrics": status.get("chain_metrics") or {},
        "index_bar_source": status.get("index_bar_source") or {},
        "signals": status.get("signals"),
        "shadow": status.get("shadow"),
        "llm_status": status.get("llm_status"),
        "live_chain": live_chain,
        "started_at_ist": pids.get("started_at_ist"),
        "flags": pids.get("flags"),
        "honesty": [
            "PAPER only. P/L is not a fill.",
            "KEEP_ALL STRAT-001–014. NO_PROMOTE.",
            "This page never prints tokens.",
        ],
    }
