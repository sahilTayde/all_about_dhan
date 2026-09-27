"""Offline scorer: LLM verdict precision against paper trade outcomes. Reads files only.

    python -m desk_ml.llm_analyst.scorer --log data/llm_analyst/calls.jsonl --trades closed_trades.json

Each filled trade is matched to the latest `ok` verdict on the same underlying and side whose tick is
at or before the trade's open and at most `--window-s` earlier. A win is net P&L > 0.
Agree precision = wins / agreed trades. Disagree precision = losers / disagreed trades.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

PNL_KEYS = ("realized_pnl_inr", "net_pnl_inr", "net_pnl", "pnl_inr", "pnl")
OPEN_KEYS = ("opened_ts", "entry_ts", "open_ts")


def read_rows(path: Path) -> list[dict[str, Any]]:
    """JSONL, a JSON list, or a JSON object with `closed_trades` / `trades`."""
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text[0] in "[{":
        try:
            blob = json.loads(text)
        except json.JSONDecodeError:
            blob = None
        if isinstance(blob, list):
            return [r for r in blob if isinstance(r, dict)]
        if isinstance(blob, dict):
            rows = blob.get("closed_trades") or blob.get("trades")
            return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else [blob]
    out = []
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _first(row: dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    for k in keys:
        try:
            if row.get(k) is not None:
                return float(row[k])
        except (TypeError, ValueError):
            continue
    return None


def _ratio(num: int, den: int) -> Optional[float]:
    return round(num / den, 4) if den else None


def score(calls: Sequence[dict[str, Any]], trades: Sequence[dict[str, Any]], *, window_s: float = 300.0) -> dict[str, Any]:
    verdicts: dict[str, dict[str, Any]] = {}
    statuses: dict[str, int] = {}
    for row in calls:
        statuses[str(row.get("status"))] = statuses.get(str(row.get("status")), 0) + 1
        v = row.get("verdict") or {}
        if row.get("status") == "ok" and isinstance(v, dict) and row.get("tick_ts") is not None:
            verdicts.setdefault(str(row.get("context_hash")), row)
    rows = list(verdicts.values())
    counts = {"agree": [0, 0], "disagree": [0, 0], "abstain": [0, 0]}  # [n, wins]
    matched_hashes: set[str] = set()
    n_trades = 0
    for t in trades:
        if t.get("filled") is False:
            continue
        opened, pnl = _first(t, OPEN_KEYS), _first(t, PNL_KEYS)
        if opened is None or pnl is None:
            continue
        n_trades += 1
        und, side = str(t.get("underlying") or "").upper(), t.get("side")
        best = None
        for r in rows:
            ts = float(r["tick_ts"])
            if str(r.get("underlying") or "").upper() == und and r.get("side") == side and 0 <= opened - ts <= window_s:
                if best is None or ts > float(best["tick_ts"]):
                    best = r
        if best is None:
            continue
        matched_hashes.add(str(best.get("context_hash")))
        c = counts[best["verdict"]["verdict"]]
        c[0] += 1
        c[1] += int(pnl > 0)
    n_ag, w_ag = counts["agree"]
    n_dis, w_dis = counts["disagree"]
    matched = n_ag + n_dis + counts["abstain"][0]
    wins = w_ag + w_dis + counts["abstain"][1]
    return {
        "calls": len(calls),
        "call_status": statuses,
        "verdict_rows": len(rows),
        "verdicts_without_trade": len(rows) - len(matched_hashes),
        "trades": n_trades,
        "trades_matched": matched,
        "base_rate_win": _ratio(wins, matched),
        "agree": {"n": n_ag, "wins": w_ag, "precision": _ratio(w_ag, n_ag)},
        "disagree": {"n": n_dis, "losers": n_dis - w_dis, "precision": _ratio(n_dis - w_dis, n_dis)},
        "abstain": {"n": counts["abstain"][0], "wins": counts["abstain"][1]},
        "window_s": window_s,
        "note": "Offline paper scoring. Small samples are noise; not a promotion gate.",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", required=True, type=Path, help="LLM call log JSONL")
    ap.add_argument("--trades", required=True, type=Path, help="closed trades: JSONL, JSON list, or replay board JSON")
    ap.add_argument("--window-s", type=float, default=300.0)
    args = ap.parse_args(argv)
    print(json.dumps(score(read_rows(args.log), read_rows(args.trades), window_s=args.window_s), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
