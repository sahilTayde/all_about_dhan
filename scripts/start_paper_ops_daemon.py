#!/usr/bin/env python3
"""Detach PAPER market-hours + ops monitor as session leaders (macOS-safe).

Production-like PAPER signal generation (NOT live order placement).
Soft-default LLM when OPENAI_API_KEY present (no --no-llm).
--live-chain when Dhan credentials load from .env.
Never prints secrets. ExecutionClient still refuses place/modify/cancel.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo

    def ist_now() -> str:
        return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
except Exception:  # pragma: no cover
    def ist_now() -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

ROOT = Path(__file__).resolve().parents[1]
RECON = ROOT / "data" / "recon"
VENV_PY = ROOT / ".venv" / "bin" / "python"
PID_FILE = RECON / "paper_ops_pids.json"
RESTART_FLAG = RECON / "paper_ops_restart_once.flag"


def _spawn(cmd: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(log_path, "a", buffering=1)
    fh.write(f"\n# spawn {ist_now()} cmd={' '.join(cmd)}\n")
    fh.flush()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("TAI_LLM_COOLDOWN_PATH", str(RECON / "llm_cooldown.json"))
    env.setdefault("NEWS_VETO_ENABLED", "false")
    # New session so Cursor/shell teardown does not SIGHUP the child.
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=fh,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
        close_fds=True,
    )
    return int(proc.pid)


def _openai_key_present() -> bool:
    try:
        sys.path.insert(0, str(ROOT / "packages" / "trading_agents_india" / "src"))
        from trading_agents_india.config import load_settings

        return bool(load_settings().openai_key_present)
    except Exception:
        return bool((os.environ.get("OPENAI_API_KEY") or "").strip())


def _dhan_live_chain_ok() -> bool:
    """Boolean only — never print token values."""
    try:
        sys.path.insert(0, str(ROOT / "packages" / "dhan-client" / "src"))
        from dhan_client.config import load_settings as load_dhan

        s = load_dhan()
        return bool(s.credentials.has_access)
    except Exception:
        return False


def build_paper_cmd(*, live_chain: bool, tick_seconds: int = 90, max_ticks: int = 900) -> list[str]:
    """Market-hours PAPER cmd. LLM soft-defaults when key present (omit --no-llm).

    Soft defaults (2026-09-07): prefer-desk ON; gather-news OFF (pre-market owns
    news); tick floor 90s when LLM (clamped in __main__ too). Do not pass
    --gather-news unless founder asks.
    """
    cmd = [
        str(VENV_PY),
        "-u",
        "-m",
        "trading_agents_india",
        "market-hours",
        "--mode",
        "PAPER",
        "--tick-seconds",
        str(max(90, int(tick_seconds))),
        "--max-ticks",
        str(max_ticks),
        # Soft-default: prefer-desk on; gather-news OFF; LLM on if key (force --use-llm).
        "--use-llm",
        "--no-gather-news",
    ]
    if live_chain:
        cmd.append("--live-chain")
    return cmd


def main() -> int:
    RECON.mkdir(parents=True, exist_ok=True)
    # Fresh restart allowance for monitor auto-recover.
    if RESTART_FLAG.exists():
        RESTART_FLAG.unlink()

    paper_log = RECON / "paper_market_hours_ops.log"
    mon_log = RECON / "paper_ops_monitor.log"
    bt_log = RECON / "paper_offline_backtest_ops.log"
    analysis_log = RECON / "paper_analysis_loop_ops.log"

    openai_on = _openai_key_present()
    live_chain = _dhan_live_chain_ok()
    # P0-4: 90s tick when LLM; gather-news soft-default OFF (omit flag).
    paper_cmd = build_paper_cmd(live_chain=live_chain, tick_seconds=90, max_ticks=900)
    mon_cmd = [
        str(VENV_PY),
        "-u",
        str(ROOT / "scripts" / "paper_ops_monitor.py"),
        "--interval",
        "25",
        "--allow-restart",
    ]
    # One-shot offline rollup (idempotent); labeled NO_PROMOTE by the tool itself.
    bt_cmd = [
        str(VENV_PY),
        "-u",
        "-m",
        "agent_rag",
        "paper-backtest",
        "--day",
        "2026-09-07",
        "--no-openai",  # avoid burning LLM budget on rollup; market-hours owns LLM
    ]
    # Slow background DI/label loop — offline only, NO_PROMOTE.
    analysis_cmd = [
        str(VENV_PY),
        "-u",
        str(ROOT / "scripts" / "paper_analysis_loop.py"),
        "--interval",
        "300",
    ]

    paper_pid = _spawn(paper_cmd, paper_log)
    mon_pid = _spawn(mon_cmd, mon_log)
    bt_pid = _spawn(bt_cmd, bt_log)
    analysis_pid = _spawn(analysis_cmd, analysis_log)

    flag_parts = [
        "--use-llm" if openai_on else "(LLM soft-default off: no OPENAI_API_KEY)",
        "--live-chain" if live_chain else "(no --live-chain: Dhan credentials missing)",
        "--tick-seconds 90",
        "--max-ticks 900",
        "(--no-gather-news; prefer-desk soft-default ON; NEWS_VETO_ENABLED=false)",
        "(real clock; no --simulate; no --stop-outside-shell)",
    ]
    payload = {
        "paper_market_hours": paper_pid,
        "ops_monitor": mon_pid,
        "offline_backtest": bt_pid,
        "analysis_loop": analysis_pid,
        "paper_log": str(paper_log),
        "monitor_log": str(mon_log),
        "backtest_log": str(bt_log),
        "analysis_log": str(analysis_log),
        "started_at_ist": ist_now(),
        "mode": "PAPER",
        "flags": " ".join(flag_parts),
        "paper_cmd": " ".join(paper_cmd),
        "simulate": False,
        "llm_enabled": openai_on,
        "live_chain": live_chain,
        "openai": "enabled via soft-default/--use-llm" if openai_on else "disabled (no key)",
        "openai_model_hint": "OPENAI_MODEL / gpt-6-astra if configured",
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "promote": "NO_PROMOTE",
        "orders": "REFUSED",
        "launcher": "scripts/start_paper_ops_daemon.py",
    }
    PID_FILE.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
