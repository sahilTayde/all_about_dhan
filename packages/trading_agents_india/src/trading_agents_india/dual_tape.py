"""Dual tape: INDEX 1m + ATM CE/PE LTP + compact chain, then desk divergence.

One program. Default poll 45s (clamp 30–60). Zero LLM on this path.
ExecutionClient stays SafeMode. RETUNE_GATE: no production param writes.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from trading_agents_india.config import Settings, load_settings
from trading_agents_india.desk_divergence import DivergenceNote, judge_tick
from trading_agents_india.hooks.chain import watch_chain
from trading_agents_india.hooks.index_bars import fetch_index_bars
from trading_agents_india.ledger import append_jsonl, paper_watch_root
from trading_agents_india.paper_ledger import PaperLedger
from trading_agents_india.premium_tape import gather_premium_tape, load_tape_bars
from trading_agents_india.session_clock import (
    DEFAULT_TICK_SECONDS,
    IST,
    clamp_tick_seconds,
    now_ist,
    snapshot,
)

UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")
MIX_ID = "DUAL-TAPE"
STOP_FLAG_NAME = "paper_dual_tape_STOPPED.flag"
RUN_FLAG_NAME = "paper_dual_tape_RUNNING.flag"
LEGACY_STOP_FLAG = "paper_ops_STOPPED.flag"


def recon_dir(repo_root: Path) -> Path:
    path = repo_root / "data" / "recon"
    path.mkdir(parents=True, exist_ok=True)
    return path


def stop_flag_path(repo_root: Path) -> Path:
    return recon_dir(repo_root) / STOP_FLAG_NAME


def run_flag_path(repo_root: Path) -> Path:
    return recon_dir(repo_root) / RUN_FLAG_NAME


def legacy_stop_note(repo_root: Path) -> dict[str, Any]:
    path = recon_dir(repo_root) / LEGACY_STOP_FLAG
    if not path.is_file():
        return {"legacy_paper_ops_stopped": False}
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        text = ""
    return {
        "legacy_paper_ops_stopped": True,
        "legacy_flag": str(path),
        "legacy_note": text[:400],
        "legacy_meaning": (
            "Old LLM market-hours / paper_ops loop was halted 2026-09-10. "
            "This dual-tape program is a separate founder-asked start: no LLM, "
            "no Dhan orders, MIX-DEFAULT-BUY unchanged."
        ),
    }


def write_run_flag(repo_root: Path, *, pid: int, extra: Optional[dict[str, Any]] = None) -> Path:
    payload = {
        "pid": pid,
        "started_at_ist": now_ist().isoformat(timespec="seconds"),
        "stop_flag": str(stop_flag_path(repo_root)),
        "how_to_stop": (
            f"touch {stop_flag_path(repo_root)}  # then the loop exits on the next tick"
        ),
        "orders": "refused",
        "llm": False,
        "promote": "NO_PROMOTE",
        **(extra or {}),
        **legacy_stop_note(repo_root),
    }
    path = run_flag_path(repo_root)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def clear_run_flag(repo_root: Path) -> None:
    path = run_flag_path(repo_root)
    if path.is_file():
        path.unlink()


def founder_stop_requested(repo_root: Path) -> bool:
    return stop_flag_path(repo_root).is_file()


def _bar_close(bar: Any) -> Optional[float]:
    if bar is None:
        return None
    val = getattr(bar, "close", None)
    if val is None and isinstance(bar, dict):
        val = bar.get("close")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _bar_dict(bar: Any) -> Optional[dict[str, Any]]:
    if bar is None:
        return None
    keys = ("ts", "open", "high", "low", "close", "volume")
    if hasattr(bar, "__dict__") or hasattr(bar, "__dataclass_fields__"):
        out = {}
        for k in keys:
            out[k] = getattr(bar, k, None)
        return out
    if isinstance(bar, dict):
        return {k: bar.get(k) for k in keys}
    return None


@dataclass
class UnderlyingSnap:
    underlying: str
    as_of_ist: str
    index_ltp: Optional[float] = None
    index_1m: Optional[dict[str, Any]] = None
    index_source: str = "unavailable"
    atm_ce_ltp: Optional[float] = None
    atm_pe_ltp: Optional[float] = None
    atm_strike: Optional[float] = None
    expiry: Optional[str] = None
    premium_source: str = "unavailable"
    chain_source: str = "unavailable"
    chain_spot: Optional[float] = None
    pcr_oi: Optional[float] = None
    strike_count: int = 0
    chain_lean: Optional[str] = None
    # Greeks: only persist if Dhan/parser sent them; else null. Never invent.
    atm_ce_iv: Optional[float] = None
    atm_pe_iv: Optional[float] = None
    atm_ce_delta: Optional[float] = None
    atm_pe_delta: Optional[float] = None
    atm_ce_gamma: Optional[float] = None
    atm_pe_gamma: Optional[float] = None
    index_delta: Optional[float] = None
    ce_delta: Optional[float] = None
    pe_delta: Optional[float] = None
    stale: bool = False
    wrong_strike: bool = False
    data_gaps: list[str] = field(default_factory=list)
    layer: str = "SOURCE_FACT"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _prev_latest(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    rows = blob.get("underlyings") if isinstance(blob, dict) else None
    if not isinstance(rows, list):
        return {}
    return {str(r.get("underlying")): r for r in rows if isinstance(r, dict)}


def gather_underlying(
    underlying: str,
    *,
    prefer_live: bool,
    simulate: bool,
    prev: Optional[dict[str, Any]] = None,
    clock_in_shell: bool = False,
) -> UnderlyingSnap:
    und = underlying.upper()
    as_of = now_ist().isoformat(timespec="seconds")
    gaps: list[str] = []
    live = bool(prefer_live) and not simulate

    bars = fetch_index_bars(und, prefer_live=live)
    gaps.extend(bars.data_gaps)
    last_bar = bars.bars[-1] if bars.bars else None
    index_ltp = bars.last_close
    tape = gather_premium_tape(und, prefer_live=live, strike_label="ATM")
    gaps.extend(tape.data_gaps)
    today = now_ist().date().isoformat()
    ce_bars = load_tape_bars(und, day=today, side="ce", strike_label="ATM")
    pe_bars = load_tape_bars(und, day=today, side="pe", strike_label="ATM")
    if not ce_bars:
        # After-hours / live miss: last cached day on disk (any).
        from trading_agents_india.premium_tape import tape_dir

        folder = tape_dir()
        matches = sorted(folder.glob(f"{und}_ATM_1m_*.json"))
        if matches:
            day = matches[-1].name.rsplit("_", 1)[-1].removesuffix(".json")
            ce_bars = load_tape_bars(und, day=day, side="ce")
            pe_bars = load_tape_bars(und, day=day, side="pe")
            gaps.append(f"cache: using premium tape day {day}")
    ce_ltp = _bar_close(ce_bars[-1]) if ce_bars else None
    pe_ltp = _bar_close(pe_bars[-1]) if pe_bars else None
    if ce_ltp is None and simulate:
        ce_ltp = 100.0
        pe_ltp = 102.0
        if index_ltp is None:
            index_ltp = {"NIFTY": 25000.0, "BANKNIFTY": 55000.0, "SENSEX": 82000.0}.get(und, 1.0)
        gaps.append("simulate: fixture LTP (not Dhan)")

    chain = watch_chain(und, prefer_live=live)
    gaps.extend(chain.data_gaps)
    if chain.atm_ce_ltp is not None:
        ce_ltp = float(chain.atm_ce_ltp)
    if chain.atm_pe_ltp is not None:
        pe_ltp = float(chain.atm_pe_ltp)
    if chain.spot is not None and index_ltp is None:
        index_ltp = float(chain.spot)

    stale = (not clock_in_shell) or (
        live and bars.source == "unavailable" and tape.source != "dhan_rollingoption_1m"
    )
    if simulate and not clock_in_shell:
        stale = True

    prev = prev or {}
    prev_strike = prev.get("atm_strike")
    wrong = False
    if chain.atm_strike is None and ce_ltp is None and pe_ltp is None:
        gaps.append("DATA_INSUFFICIENT: no ATM strike and no CE/PE LTP")
    elif prev_strike is not None and chain.atm_strike is not None:
        try:
            if abs(float(chain.atm_strike) - float(prev_strike)) > 0:
                # Rolling ATM is expected; not wrong unless LTP side missing.
                if ce_ltp is None or pe_ltp is None:
                    wrong = True
        except (TypeError, ValueError):
            wrong = True

    def _d(cur: Optional[float], key: str) -> Optional[float]:
        raw = prev.get(key)
        if cur is None or raw is None:
            return None
        try:
            return float(cur) - float(raw)
        except (TypeError, ValueError):
            return None

    snap = UnderlyingSnap(
        underlying=und,
        as_of_ist=as_of,
        index_ltp=index_ltp,
        index_1m=_bar_dict(last_bar),
        index_source=bars.source,
        atm_ce_ltp=ce_ltp,
        atm_pe_ltp=pe_ltp,
        atm_strike=chain.atm_strike,
        expiry=chain.expiry,
        premium_source=tape.source,
        chain_source=chain.source,
        chain_spot=chain.spot,
        pcr_oi=chain.pcr_oi,
        strike_count=int(chain.strike_count or 0),
        chain_lean=chain.chain_lean,
        atm_ce_iv=None,
        atm_pe_iv=None,
        atm_ce_delta=None,
        atm_pe_delta=None,
        atm_ce_gamma=None,
        atm_pe_gamma=None,
        index_delta=_d(index_ltp, "index_ltp"),
        ce_delta=_d(ce_ltp, "atm_ce_ltp"),
        pe_delta=_d(pe_ltp, "atm_pe_ltp"),
        stale=stale,
        wrong_strike=wrong,
        data_gaps=list(dict.fromkeys(gaps)),
        layer="SOURCE_FACT" if bars.source.startswith("dhan") or tape.source.startswith("dhan") else "HYPOTHESIS",
    )
    return snap


def persist_tick(
    repo_root: Path,
    *,
    tick_index: int,
    clock: dict[str, Any],
    snaps: list[UnderlyingSnap],
    notes: list[DivergenceNote],
    simulated: bool,
    kb_path: Path,
) -> dict[str, str]:
    day = now_ist().date().isoformat()
    root = paper_watch_root(repo_root)
    mix_dir = root / MIX_ID
    mix_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "mix_id": MIX_ID,
        "tick_index": tick_index,
        "clock": clock,
        "simulated": simulated,
        "as_of_ist": now_ist().isoformat(timespec="seconds"),
        "underlyings": [s.to_dict() for s in snaps],
        "desk": [n.to_dict() for n in notes],
        "orders": "refused",
        "llm": False,
        "promote": False,
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "customer_mix": "MIX-DEFAULT-BUY unchanged",
    }
    jsonl = append_jsonl(mix_dir / f"{day}.jsonl", row)
    latest = mix_dir / "latest.json"
    latest.write_text(json.dumps(row, indent=2, default=str, ensure_ascii=False) + "\n", encoding="utf-8")

    overlay_path = ""
    try:
        from desk_ml.overlay import attach_after_tick

        written = attach_after_tick(repo_root, mix_dir)
        if written is not None:
            overlay_path = str(written)
    except Exception:  # noqa: BLE001 — overlay is fail-soft; dual-tape must still persist
        overlay_path = ""

    notes_path = mix_dir / f"{day}.notes.md"
    block = [
        f"## Tick {tick_index} — {row['as_of_ist']}",
        "",
    ]
    for n in notes:
        block.append(f"- **{n.underlying}** `{n.verdict}` / `{n.reason_code}`: {n.dealer_note}")
    block.append("")
    with notes_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(block) + "\n")

    store = DualTapeStore(kb_path)
    store.append(row)

    ledger = PaperLedger(
        kb_path,
        repo_root / "data" / "recon" / "paper_ledger" / f"{day}.jsonl",
    )
    for n in notes:
        ledger.append(
            "DESK_DIVERGENCE",
            n.to_dict(),
            {
                "tick_index": tick_index,
                "as_of_ist": row["as_of_ist"],
                "underlying": n.underlying,
            },
        )

    return {
        "jsonl": str(jsonl),
        "latest": str(latest),
        "notes": str(notes_path),
        "sqlite": str(kb_path),
        "overlay": overlay_path,
    }


class DualTapeStore:
    """Compact ticks in trading_agents_india.sqlite — never writes production params."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS dual_tape_ticks (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  as_of_ist TEXT NOT NULL,
                  tick_index INTEGER NOT NULL,
                  payload_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path))

    def append(self, row: dict[str, Any]) -> None:
        created = datetime.now(IST).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO dual_tape_ticks (as_of_ist, tick_index, payload_json, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    str(row.get("as_of_ist") or ""),
                    int(row.get("tick_index") or 0),
                    json.dumps(row, default=str, ensure_ascii=False),
                    created,
                ),
            )


@dataclass
class DualTapeResult:
    ticks: list[dict[str, Any]]
    tick_seconds: int
    simulated: bool
    stopped_reason: str
    paths: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick_count": len(self.ticks),
            "tick_seconds": self.tick_seconds,
            "simulated": self.simulated,
            "stopped_reason": self.stopped_reason,
            "paths": self.paths,
            "ticks": self.ticks,
            "execution": "refused",
            "llm": False,
            "promote": "NO_PROMOTE",
            "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
            "customer_mix": "MIX-DEFAULT-BUY unchanged",
        }


def run_dual_tape_loop(
    *,
    underlyings: Optional[Sequence[str]] = None,
    tick_seconds: int = DEFAULT_TICK_SECONDS,
    max_ticks: int = 1,
    simulate: bool = False,
    prefer_live_chain: bool = False,
    persist: bool = True,
    stop_outside_shell: bool = False,
    sleep_fn: Callable[[float], None] = time.sleep,
    settings: Optional[Settings] = None,
    write_run_flag_on_start: bool = True,
) -> DualTapeResult:
    settings = settings or load_settings()
    tick_seconds = clamp_tick_seconds(tick_seconds)
    names = tuple(u.strip().upper() for u in (underlyings or UNDERLYINGS) if u.strip())
    if not names:
        names = UNDERLYINGS

    ticks: list[dict[str, Any]] = []
    stopped = "completed_max_ticks"
    latest_path = paper_watch_root(settings.repo_root) / MIX_ID / "latest.json"
    prev_map = _prev_latest(latest_path)
    last_paths: dict[str, str] = {}

    if write_run_flag_on_start:
        write_run_flag(
            settings.repo_root,
            pid=os.getpid(),
            extra={
                "tick_seconds": tick_seconds,
                "simulate": simulate,
                "prefer_live_chain": prefer_live_chain,
                "max_ticks": max_ticks,
            },
        )

    try:
        i = 0
        while True:
            if founder_stop_requested(settings.repo_root):
                stopped = "founder_stop_flag"
                break
            clock = snapshot()
            if stop_outside_shell and not clock.in_session_shell and not simulate:
                stopped = "outside_session_shell"
                break

            snaps: list[UnderlyingSnap] = []
            notes: list[DivergenceNote] = []
            for und in names:
                snap = gather_underlying(
                    und,
                    prefer_live=prefer_live_chain,
                    simulate=simulate,
                    prev=prev_map.get(und),
                    clock_in_shell=clock.in_session_shell,
                )
                note = judge_tick(
                    underlying=und,
                    index_delta=snap.index_delta,
                    ce_delta=snap.ce_delta,
                    pe_delta=snap.pe_delta,
                    stale=snap.stale,
                    wrong_strike=snap.wrong_strike,
                    data_gaps=snap.data_gaps,
                )
                snaps.append(snap)
                notes.append(note)
                prev_map[und] = snap.to_dict()

            if persist:
                last_paths = persist_tick(
                    settings.repo_root,
                    tick_index=i,
                    clock=clock.to_dict(),
                    snaps=snaps,
                    notes=notes,
                    simulated=simulate,
                    kb_path=settings.kb_path,
                )

            heartbeat = {
                "event": "dual_tape_tick",
                "tick_index": i,
                "as_of_ist": now_ist().isoformat(timespec="seconds"),
                "simulated": simulate,
                "in_session_shell": clock.in_session_shell,
                "desk": {n.underlying: {"verdict": n.verdict, "case": n.case} for n in notes},
                "index_ltp": {s.underlying: s.index_ltp for s in snaps},
                "atm_ce_ltp": {s.underlying: s.atm_ce_ltp for s in snaps},
                "atm_pe_ltp": {s.underlying: s.atm_pe_ltp for s in snaps},
                "execution": "refused",
                "llm": False,
                "promote": "NO_PROMOTE",
            }
            print(json.dumps(heartbeat, ensure_ascii=False), flush=True)
            ticks.append(heartbeat)

            i += 1
            if max_ticks > 0 and i >= max_ticks:
                stopped = "completed_max_ticks"
                break
            if not (simulate and max_ticks > 0):
                sleep_fn(float(tick_seconds))
    finally:
        if write_run_flag_on_start:
            clear_run_flag(settings.repo_root)

    return DualTapeResult(
        ticks=ticks,
        tick_seconds=tick_seconds,
        simulated=simulate,
        stopped_reason=stopped,
        paths=last_paths,
    )
