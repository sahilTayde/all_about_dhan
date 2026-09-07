#!/usr/bin/env python3
"""Slow offline analysis loop for PAPER ops.

Re-labels DATA_INSUFFICIENT strategy candidates from the day's ledger,
scans SL/target/entry construction bugs (especially INDEX_POINTS_PROXY
inversion and premium-shaped placeholders), and refreshes agent_rag
paper-backtest rollup. Writes attention items for the ops canvas.

NO_PROMOTE. Never places orders. Never prints secrets.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECON = ROOT / "data" / "recon"
LEDGER_DIR = RECON / "paper_ledger"
STATUS = RECON / "paper_analysis_loop_status.json"
LOG = RECON / "paper_analysis_loop_ops.log"
ATTENTION = RECON / "paper_attention_bugs.json"
ATTENTION_LOG = RECON / "paper_attention_bugs.log"
LATEST_SIGNALS = RECON / "paper_latest_signals.json"
OPS_STATUS = RECON / "paper_ops_monitor_status.json"
STOP_FLAG = RECON / "paper_ops_STOPPED.flag"
MOCK_SIGNAL = ROOT / "apps" / "web" / "public" / "mock" / "signal.json"
VENV_PY = ROOT / ".venv" / "bin" / "python"

sys.path.insert(0, str(ROOT / "packages" / "backtest" / "src"))


def _ist_day() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ist_now() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
    except Exception:
        return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _customer_veto_reasons(*sources, limit: int = 3) -> list[str]:
    """Dedupe hold reasons; drop agent chatter (boss/tech/…) from customer banner."""
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


def _scan_di(day: str) -> dict:
    path = LEDGER_DIR / f"{day}.jsonl"
    out = {
        "day": day,
        "ledger_path": str(path),
        "candidates": 0,
        "data_insufficient": 0,
        "by_outcome": {},
        "by_candidate": {},
        "promote_false": 0,
        "signals": 0,
        "lean_counts": {},
        "ce": 0,
        "pe": 0,
        "hold": 0,
        "top_veto_reasons": {},
        "latest_as_of_ist": None,
    }
    if not path.exists():
        return out
    outcomes: Counter[str] = Counter()
    by_cand: Counter[str] = Counter()
    leans: Counter[str] = Counter()
    last_by_und: dict[str, dict] = {}
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            et = obj.get("event_type")
            if et == "SIGNAL":
                out["signals"] += 1
                lean = str(obj.get("lean") or obj.get("side") or "?").upper()
                leans[lean] += 1
                und = str(obj.get("underlying") or "?").upper()
                last_by_und[und] = obj
                out["latest_as_of_ist"] = obj.get("as_of_ist") or out["latest_as_of_ist"]
                continue
            if et != "CANDIDATE_OBSERVATION":
                continue
            out["candidates"] += 1
            outcome = str(obj.get("outcome") or "?")
            outcomes[outcome] += 1
            cid = str(obj.get("candidate_id") or obj.get("strategy_or_mix_id") or "?")
            if outcome == "DATA_INSUFFICIENT":
                out["data_insufficient"] += 1
                by_cand[cid] += 1
            if obj.get("promote") is False or obj.get("promote") is None:
                out["promote_false"] += 1
    out["by_outcome"] = dict(outcomes)
    out["by_candidate"] = dict(by_cand.most_common(12))
    out["lean_counts"] = dict(leans)
    out["ce"] = int(leans.get("BUY_CE", 0))
    out["pe"] = int(leans.get("BUY_PE", 0))
    out["hold"] = int(leans.get("HOLD", 0))
    veto_map: dict[str, list[str]] = {}
    for und, obj in last_by_und.items():
        reasons = _customer_veto_reasons(
            obj.get("top_veto_reasons"),
            obj.get("vetoes"),
            obj.get("reasons"),
            limit=3,
        )
        if reasons:
            veto_map[und] = reasons
    out["top_veto_reasons"] = veto_map
    return out


def _write_latest_signals(day: str, di: dict) -> Path:
    """Tiny snapshot for API /paper/signal veto banner (no 47MB scan)."""
    payload = {
        "day": day,
        "updated_at_ist": _ist_now(),
        "as_of_ist": di.get("latest_as_of_ist"),
        "lean_counts": di.get("lean_counts") or {},
        "signals": di.get("signals") or 0,
        "ce": di.get("ce") or 0,
        "pe": di.get("pe") or 0,
        "hold": di.get("hold") or 0,
        "top_veto_reasons": di.get("top_veto_reasons") or {},
        "ship": False,
        "note": "Scan snapshot only — NO_PROMOTE; orders REFUSED",
    }
    LATEST_SIGNALS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return LATEST_SIGNALS


def _scan_level_bugs() -> list[dict]:
    """Scan mock fixture + ledger for index-as-premium / inverted levels."""
    from backtest_engine.levels import (
        validate_customer_option_premium_slots,
        validate_index_proxy_levels,
    )

    bugs: list[dict] = []

    if MOCK_SIGNAL.exists():
        try:
            desk = json.loads(MOCK_SIGNAL.read_text())
        except Exception as exc:
            bugs.append(
                {
                    "surface": "mock/signal.json",
                    "action": "Unreadable",
                    "why": f"{type(exc).__name__}",
                    "bug": "MOCK_UNREADABLE",
                }
            )
            desk = {}
        # PAPER book must not contain FIXTURE rows
        paper_rows = (desk.get("todaysBook") or {}).get("rows") or []
        for row in paper_rows:
            mode = str(row.get("mode") or row.get("source") or "").upper()
            if mode in ("MOCK", "FIXTURE"):
                bugs.append(
                    {
                        "surface": "todaysBook",
                        "action": "Separate FIXTURE",
                        "why": f"PAPER book still has {mode} row {row.get('id')}",
                        "bug": "FIXTURE_CLUBBED_INTO_PAPER",
                    }
                )
        for und, sig in (desk.get("signals") or {}).items():
            unit = str((sig.get("ticket") or {}).get("unit") or "OPTION_PREMIUM")
            found = validate_customer_option_premium_slots(
                side=str(sig.get("side") or ""),
                entry=sig.get("entry"),
                stop=sig.get("stop"),
                target=sig.get("target"),
                underlying=str(und),
                unit=unit,
            )
            for b in found:
                bugs.append(
                    {
                        "surface": f"mock ticket {und}",
                        "action": "Quarantine index from premium slots",
                        "why": b,
                        "bug": b.split(":")[0],
                    }
                )
            # Chart index overlays are allowed; only validate if ticket still claims INDEX unit
            if "INDEX" in unit.upper() and "PREMIUM" not in unit.upper():
                for b in validate_index_proxy_levels(
                    lean=str(sig.get("side") or ""),
                    entry=sig.get("entry"),
                    stop=sig.get("stop"),
                    target=sig.get("target"),
                    underlying=str(und),
                ):
                    bugs.append(
                        {
                            "surface": f"mock ticket {und}",
                            "action": "Fix levels",
                            "why": b,
                            "bug": b.split(":")[0],
                        }
                    )
        for row in (desk.get("fixtureBook") or {}).get("rows") or []:
            found = validate_customer_option_premium_slots(
                side=str(row.get("side") or ""),
                entry=row.get("entry"),
                stop=row.get("stop"),
                target=row.get("target"),
                underlying=str(row.get("underlying") or ""),
                unit=str(row.get("unit") or "OPTION_PREMIUM"),
            )
            for b in found:
                bugs.append(
                    {
                        "surface": f"fixtureBook {row.get('id')}",
                        "action": "Quarantine fixture premium slots",
                        "why": b,
                        "bug": b.split(":")[0],
                    }
                )

    day = _ist_day()
    path = LEDGER_DIR / f"{day}.jsonl"
    if path.exists():
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("event_type") not in ("SIGNAL", "SHADOW_TRADE"):
                    continue
                if obj.get("entry") is None and obj.get("stop") is None:
                    continue
                found = validate_customer_option_premium_slots(
                    side=str(obj.get("lean") or obj.get("side") or ""),
                    entry=obj.get("entry"),
                    stop=obj.get("stop"),
                    target=obj.get("target"),
                    underlying=str(obj.get("underlying") or ""),
                    unit=str(obj.get("unit") or "OPTION_PREMIUM"),
                )
                for b in found:
                    bugs.append(
                        {
                            "surface": f"ledger {obj.get('event_type')} {obj.get('underlying')}",
                            "action": "Refuse index-as-premium",
                            "why": b,
                            "bug": b.split(":")[0],
                        }
                    )
                    if len(bugs) >= 24:
                        return bugs
    return bugs


def _run_paper_backtest(day: str) -> dict:
    import subprocess

    cmd = [
        str(VENV_PY),
        "-u",
        "-m",
        "agent_rag",
        "paper-backtest",
        "--day",
        day,
        "--no-openai",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-400:],
            "stderr_tail": (proc.stderr or "")[-400:],
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}



def _write_attention_queue(day: str, di: dict, level_bugs: list, items: list) -> Path:
    """P1: owned queue with done-when. Scan ≠ ship."""
    path = RECON / f"ATTENTION_QUEUE_{day}.md"
    lines = [
        f"# Attention queue — {day}",
        "",
        "**Mode:** PAPER · **NO_PROMOTE** · orders **REFUSED**",
        "**Honesty:** This loop **scans**; it does **not** ship code fixes.",
        "",
        "| ID | Owner | Issue | Done when | Status |",
        "|----|-------|-------|-----------|--------|",
    ]
    rows = []
    if di.get("data_insufficient") and di.get("candidates"):
        ratio = di["data_insufficient"] / max(1, di["candidates"])
        if ratio >= 0.7:
            rows.append(
                (
                    "P0-DI",
                    "04+06+trading_agents_india",
                    f"DI ratio {ratio:.0%} ({di['data_insufficient']}/{di['candidates']})",
                    "Unbound STRAT DI rows drop ≥10× or named MIX binder under PAPER_WATCH",
                    "OPEN — scan only, no ship",
                )
            )
    for i, b in enumerate(level_bugs[:6]):
        bug = str(b.get("bug") or "LEVEL")
        rows.append(
            (
                f"P1-{bug[:16]}-{i+1}",
                "07",
                f"{b.get('surface')}: {b.get('why')}",
                b.get("action") or "Fix or PARK with reason",
                "OPEN — scan only, no ship",
            )
        )
    if not rows:
        rows.append(("NONE", "00", "No open attention items", "n/a", "CLEAR"))
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
    lines += [
        "",
        "## Explicit no-ship",
        "",
        "This analysis loop does **not** open PRs, patch fixtures, or bind STRAT evaluators.",
        "See `PROCESS_FIXES_SHIPPED_*.md` / CONTINUE_NEXT_CHAT for what actually shipped.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _ops_llm_error() -> str:
    if not OPS_STATUS.is_file():
        return "n/a"
    try:
        blob = json.loads(OPS_STATUS.read_text(encoding="utf-8"))
    except Exception:
        return "n/a"
    return str(blob.get("llm_last_error_class") or blob.get("llm_status") or "n/a")


def _write_founder_digest(day: str, di: dict, level_bugs: list, bt: dict) -> Path:
    """P1-2: ≤15 lines — CE/PE/HOLD, DI%, LLM, top P0, shipped paths. Scan ≠ ship."""
    path = RECON / f"FOUNDER_DIGEST_{day}.md"
    cand = int(di.get("candidates") or 0)
    di_n = int(di.get("data_insufficient") or 0)
    di_pct = f"{(100.0 * di_n / cand):.0f}%" if cand else "n/a"
    top_p0 = "none"
    if cand and di_n / max(1, cand) >= 0.7:
        top_p0 = "P0-DI unbound STRAT evaluators (KEEP_ALL; scan only — workstream C)"
    elif level_bugs:
        top_p0 = f"P1 levels: {level_bugs[0].get('bug')}"
    stop = "yes" if STOP_FLAG.exists() else "no"
    lines = [
        f"# Founder digest — {day}",
        "",
        f"- Updated: {_ist_now()} · stop_flag={stop}",
        "- Mode: PAPER · NO_PROMOTE · orders REFUSED · **ship=false** (scan only)",
        f"- Signals: CE={di.get('ce', 0)} PE={di.get('pe', 0)} HOLD={di.get('hold', 0)} "
        f"(total {di.get('signals', 0)})",
        f"- Candidates: {cand} · DI: {di_n} ({di_pct}) · outcomes: {di.get('by_outcome')}",
        f"- LLM (ops status): {_ops_llm_error()}",
        f"- Top P0: {top_p0}",
        f"- Level bugs this pass: {len(level_bugs)} (scan only — no auto-patch)",
        f"- paper-backtest ok: {bt.get('ok')} rc={bt.get('returncode')}",
        "- Shipped: `data/recon/PROCESS_FIXES_SHIPPED_2026-09-07.md`",
        f"- Snapshot: `{LATEST_SIGNALS.name}` · EOD: `python -m agent_rag eod-recon --day {day} --offline`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def once() -> dict:
    day = _ist_day()
    di = _scan_di(day)
    level_bugs = _scan_level_bugs()
    bt = _run_paper_backtest(day)
    items: list[dict] = []
    if di.get("data_insufficient") and di.get("candidates"):
        ratio = di["data_insufficient"] / max(1, di["candidates"])
        if ratio >= 0.7:
            items.append(
                {
                    "surface": "Chain / news inputs",
                    "action": "Tune data path",
                    "why": (
                        f"DI ratio {ratio:.0%} "
                        f"({di['data_insufficient']}/{di['candidates']})"
                    ),
                }
            )
    attention = {
        "updated_at_ist": _ist_now(),
        "mode": "PAPER",
        "promote": "NO_PROMOTE",
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "orders": "REFUSED",
        "level_bugs": level_bugs,
        "items": items,
        "note": (
            "FIXED: customer ticket Entry/SL/Target = option premium only "
            "(still DATA_INSUFFICIENT when premium LTP missing). "
            "Index overlays stay on the chart — never masquerade as premium. "
            "Do not invent premium fills."
        ),
    }
    latest_path = _write_latest_signals(day, di)
    queue_path = _write_attention_queue(day, di, level_bugs, items)
    digest_path = _write_founder_digest(day, di, level_bugs, bt)
    attention["ship"] = False
    attention["honesty"] = "scan_only"
    attention["no_ship_reason"] = (
        "Analysis loop is scan/rollup only — does not ship code, bind STRATs, "
        "or unlock CE/PE. "
        f"Queue: {queue_path.name}; digest: {digest_path.name}; "
        f"latest: {latest_path.name}"
    )
    ATTENTION.write_text(json.dumps(attention, indent=2) + "\n")
    with ATTENTION_LOG.open("a") as fh:
        fh.write(
            f"{attention['updated_at_ist']} level_bugs={len(level_bugs)} "
            f"items={len(items)} di={di.get('data_insufficient')}\n"
        )
        for b in level_bugs[:8]:
            fh.write(f"  BUG {b.get('bug')}: {b.get('surface')} — {b.get('why')}\n")

    payload = {
        "updated_at_ist": attention["updated_at_ist"],
        "mode": "PAPER",
        "promote": "NO_PROMOTE",
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "orders": "REFUSED",
        "di_scan": di,
        "level_bugs_count": len(level_bugs),
        "paper_backtest": {"ok": bt.get("ok"), "returncode": bt.get("returncode")},
        "attention_path": str(ATTENTION),
        "note": "Offline DI/level scan / rollup only — UNVALIDATED; no ship; no live orders",
        "attention_queue": str(RECON / f"ATTENTION_QUEUE_{day}.md"),
        "founder_digest": str(RECON / f"FOUNDER_DIGEST_{day}.md"),
        "latest_signals": str(LATEST_SIGNALS),
        "ship": False,
        "signal_leans": {
            "ce": di.get("ce", 0),
            "pe": di.get("pe", 0),
            "hold": di.get("hold", 0),
            "signals": di.get("signals", 0),
        },
    }
    STATUS.write_text(json.dumps(payload, indent=2) + "\n")
    with LOG.open("a") as fh:
        fh.write(
            f"{payload['updated_at_ist']} di={di.get('data_insufficient')} "
            f"cand={di.get('candidates')} level_bugs={len(level_bugs)} "
            f"bt_ok={bt.get('ok')}\n"
        )
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="PAPER offline DI/analysis loop")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=300)
    ap.add_argument("--max-loops", type=int, default=0)
    args = ap.parse_args()
    RECON.mkdir(parents=True, exist_ok=True)
    loops = 0
    while True:
        try:
            once()
        except Exception as exc:
            with LOG.open("a") as fh:
                fh.write(f"{_ist_now()} ERROR {type(exc).__name__}: {exc}\n")
        loops += 1
        if args.once or (args.max_loops and loops >= args.max_loops):
            break
        time.sleep(max(60, int(args.interval)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
