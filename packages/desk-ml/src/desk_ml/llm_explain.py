"""Async LLM trade explainer. Log only. Never vetoes a paper fill.

Paper-slot trades only. Uses desk_ml.llm_judge plumbing (gpt-4o-mini, OPENAI key
from env). Missing key skips. The caller returns before the model answers.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from desk_ml.llm_judge import (
    ACTOR,
    EXPLAIN_SYSTEM,
    IST,
    LlmJudge,
    SCHEMA,
    CompleteFn,
    _board_fingerprint,
    _ist_parts,
    _journal_row,
    _num,
    _phase,
    _snap_map,
    append_judge_row,
    build_market_snapshot,
    build_pick_snapshot,
    load_config,
    load_morning_context,
    paper_slot_ids,
    plain_market_type,
)

log = logging.getLogger("desk_ml.llm_explain")

_POOL: Optional[ThreadPoolExecutor] = None
_POOL_LOCK = threading.Lock()


def _pool() -> ThreadPoolExecutor:
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            _POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="llm-explain")
        return _POOL


def reset_explain_pool() -> None:
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None:
            _POOL.shutdown(wait=False, cancel_futures=True)
        _POOL = None


def _trade_day_hhmm(trade: Mapping[str, Any], fallback: datetime) -> tuple[str, str, int]:
    opened = trade.get("opened_ist") or trade.get("opened_ts") or trade.get("ts")
    return _ist_parts(opened, fallback)


def _is_paper_slot(trade: Mapping[str, Any], slots: frozenset[str]) -> bool:
    setup = str(trade.get("book_id") or trade.get("rule_id") or trade.get("setup") or trade.get("strategy_id") or "")
    if setup in slots:
        return True
    source = str(trade.get("source") or "")
    return source == "paper_slot" or bool(trade.get("paper_slot"))


def collect_paper_slot_trades(
    board: Mapping[str, Any],
    *,
    root: Path,
) -> list[dict[str, Any]]:
    """Open or just-filled paper-slot tickets. Shadow rules are ignored."""
    slots = paper_slot_ids(root, allow_code_root=False)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in list(board.get("open_trades") or []) + list(board.get("closed_trades") or []):
        if not isinstance(row, Mapping):
            continue
        if not _is_paper_slot(row, slots):
            continue
        tid = str(row.get("trade_id") or "")
        if not tid or tid in seen:
            continue
        seen.add(tid)
        out.append(dict(row))
    return out


def _bars_for(root: Path, und: str, day: str) -> dict[str, Any]:
    try:
        from desk_ml.research_rules import load_atm_minutes

        return load_atm_minutes(root, und, day) or {}
    except Exception:  # noqa: BLE001 — tape miss must not block paper
        return {}


def build_explain_snapshot(
    trade: Mapping[str, Any],
    *,
    root: Path,
    board: Mapping[str, Any],
    snaps: Optional[Sequence[Any]] = None,
    prev_snaps: Optional[Sequence[Any]] = None,
    morning: Any = None,
    day: str,
    hhmm: str,
) -> dict[str, Any]:
    und = str(trade.get("underlying") or "").upper()
    side = str(trade.get("side") or "")
    snap_by = _snap_map(snaps)
    prev_by = _snap_map(prev_snaps)
    market = build_market_snapshot(
        underlying=und,
        bars=_bars_for(root, und, day),
        snap=snap_by.get(und),
        prev_snap=prev_by.get(und),
        board=board,
        morning=morning,
        hhmm=hhmm,
        side=side,
    )
    setup = str(trade.get("book_id") or trade.get("rule_id") or trade.get("setup") or "paper")
    snap = build_pick_snapshot(
        setup=setup,
        side=side,
        strike=trade.get("atm_strike") or trade.get("strike"),
        underlying=und,
        market=market,
        source="paper_slot",
        hhmm=hhmm,
        day=day,
    )
    snap["job"] = "EXPLAIN"
    snap["trade_id"] = trade.get("trade_id")
    snap["entry"] = _num(trade.get("entry"))
    return snap


def _write_explain(
    *,
    root: Path,
    trade: Mapping[str, Any],
    verdict: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    day: str,
    hhmm: str,
    ts: int,
    dedupe: str,
) -> None:
    from desk_ml.decision_journal import DecisionJournal

    und = str(trade.get("underlying") or "").upper()
    tid = str(trade.get("trade_id") or "")
    market = plain_market_type(verdict.get("market_type")) or verdict.get("market_type")
    row = {
        "schema": SCHEMA,
        "job": "EXPLAIN",
        "day": day,
        "ts": ts,
        "hhmm": hhmm,
        "underlying": und,
        "trade_id": tid,
        "setup": trade.get("book_id") or trade.get("rule_id") or trade.get("setup"),
        "side": trade.get("side"),
        "strike": trade.get("atm_strike") or trade.get("strike"),
        "source": "paper_slot",
        "explanation": verdict.get("explanation") or verdict.get("reason"),
        "market_type": market,
        "status": verdict.get("status"),
        "reason": verdict.get("reason") or verdict.get("error") or verdict.get("status"),
        "dedupe_key": dedupe,
        "context_hash": verdict.get("context_hash"),
        "cost_usd": verdict.get("cost_usd") or 0.0,
        "cached": bool(verdict.get("cached")),
        "latency_ms": verdict.get("latency_ms"),
        "prompt_version": "llm-explain-v1",
        "snapshot": snapshot if verdict.get("status") == "ok" else None,
        "orders": "REFUSED",
        "promote": False,
        "shadow": True,
        "trade": False,
        "veto": False,
    }
    append_judge_row(root, row)
    if verdict.get("status") != "ok":
        return
    DecisionJournal(root).append(
        _journal_row(
            ts=ts,
            underlying=und,
            candidate_id=tid or dedupe,
            job="EXPLAIN",
            verdict=verdict,
            trade_id=tid,
            inputs={
                "side": trade.get("side"),
                "market_type": market,
                "day_type": market,
                "phase": _phase(hhmm),
                "explanation": verdict.get("explanation"),
            },
        )
    )


def _explain_one(
    trade: Mapping[str, Any],
    *,
    root: Path,
    board: Mapping[str, Any],
    snaps: Optional[Sequence[Any]],
    prev_snaps: Optional[Sequence[Any]],
    now: datetime,
    complete_fn: Optional[CompleteFn],
    environ: Optional[Mapping[str, str]],
    judge: Optional[LlmJudge],
) -> dict[str, Any]:
    cfg = load_config(root, environ)
    owned = judge is None
    worker = judge or LlmJudge(cfg, root=root, complete_fn=complete_fn, environ=environ)
    try:
        day, hhmm, ts = _trade_day_hhmm(trade, now)
        morning = load_morning_context(root, day)
        snapshot = build_explain_snapshot(
            trade,
            root=root,
            board=board,
            snaps=snaps,
            prev_snaps=prev_snaps,
            morning=morning,
            day=day,
            hhmm=hhmm,
        )
        tid = str(trade.get("trade_id") or f"{trade.get('underlying')}:{trade.get('side')}:{hhmm}")
        dedupe = f"explain:{tid}"
        verdict = worker.review("EXPLAIN", snapshot, dedupe_key=dedupe)
        _write_explain(
            root=root,
            trade=trade,
            verdict=verdict,
            snapshot=snapshot,
            day=day,
            hhmm=hhmm,
            ts=ts,
            dedupe=dedupe,
        )
        return {**verdict, "trade_id": tid, "trade": False, "veto": False}
    finally:
        if owned:
            worker.close()


def schedule_explains(
    board: Mapping[str, Any],
    *,
    root: Path,
    snaps: Optional[Sequence[Any]] = None,
    prev_snaps: Optional[Sequence[Any]] = None,
    now: Optional[datetime] = None,
    complete_fn: Optional[CompleteFn] = None,
    environ: Optional[Mapping[str, str]] = None,
    judge: Optional[LlmJudge] = None,
    write: bool = True,
    wait: bool = False,
) -> dict[str, Any]:
    """Enqueue one explainer call per paper-slot trade. Returns before the model answers.

    ``wait=True`` is for tests only. The paper fill path always uses wait=False.
    Fingerprint of fills is checked before and after enqueue. Workers never write the board.
    """
    before = _board_fingerprint(board)
    cfg = load_config(root, environ)
    empty = {
        "schema": f"{SCHEMA}-explain",
        "job": "EXPLAIN",
        "shadow": True,
        "trade": False,
        "veto": False,
        "scheduled": 0,
        "wrote": 0,
        "orders": "REFUSED",
        "promote": False,
        "prompt": "llm-explain-v1",
        "system_lead": EXPLAIN_SYSTEM[:40],
    }
    if not cfg["shadow"] or not write:
        return empty
    stamp = now if now is not None else datetime.now(IST)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=IST)
    stamp = stamp.astimezone(IST)
    trades = collect_paper_slot_trades(board, root=root)
    if not trades:
        if _board_fingerprint(board) != before:
            raise RuntimeError("llm_explain mutated paper-slot decisions")
        return empty
    futures = []
    for trade in trades:
        fut = _pool().submit(
            _explain_one,
            dict(trade),
            root=root,
            board=dict(board),
            snaps=snaps,
            prev_snaps=prev_snaps,
            now=stamp,
            complete_fn=complete_fn,
            environ=environ,
            judge=judge,
        )
        futures.append(fut)
    if _board_fingerprint(board) != before:
        raise RuntimeError("llm_explain mutated paper-slot decisions")
    wrote = 0
    if wait:
        for fut in futures:
            try:
                out = fut.result(timeout=max(1.0, float(cfg.get("timeout_s") or 3.0) + 1.0))
                if out.get("status") == "ok":
                    wrote += 1
            except Exception:  # noqa: BLE001 — fail-soft; paper loop already returned
                log.info("llm_explain wait failed", exc_info=True)
    return {
        **empty,
        "scheduled": len(futures),
        "wrote": wrote,
        "futures": futures,
    }
