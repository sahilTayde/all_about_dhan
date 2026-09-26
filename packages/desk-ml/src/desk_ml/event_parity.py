"""Parity: the USE_EVENT_BUS path must reproduce the monolith's trade list exactly.

    # recorded dual-tape days under data/recon/paper_watch/DUAL-TAPE (local only, not in git)
    python -m desk_ml.event_parity --since 2026-09-17 --until 2026-09-25 [--kw no_new_after_minutes=870 ...]
    # committed synthetic session (what CI runs)
    python -m desk_ml.event_parity --fixture packages/desk-ml/tests/fixtures/synthetic_session_nifty.json

Both paths get identical replay kwargs; the old path is `replay_paper_scalp(use_event_bus=False)`.
Every closed-trade field must match (count, ids, timestamps, strikes, prices, P&L, reasons) and the
skip-reason counts must match. The event path's ledger must hold the same filled trades.
Exit code 0 = parity, 1 = mismatch. Paper only; no broker is called.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from desk_ml.features import Triple

IST = timezone(timedelta(hours=5, minutes=30))
PRICE_TOL = 0.025  # ledger books exchange ticks (0.05); the engine keeps unrounded limit prices
TRIPLE_FIELDS = (
    "ts", "idx_close", "ce_close", "pe_close", "atm_strike", "itm_ce_close", "itm_pe_close",
    "itm_ce_strike", "itm_pe_strike", "idx_volume", "premium_kind",
)


def _diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    return {k: (a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


def compare_boards(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    a, b = old.get("closed_trades") or [], new.get("closed_trades") or []
    if len(a) != len(b):
        problems.append(f"closed trades: old {len(a)} vs new {len(b)}")
    for n, (x, y) in enumerate(zip(a, b)):
        d = _diff(x, y)
        if d:
            problems.append(f"closed[{n}] {x.get('trade_id')}: {d}")
    oa, ob = old.get("open_trades") or [], new.get("open_trades") or []
    if [r.get("trade_id") for r in oa] != [r.get("trade_id") for r in ob]:
        problems.append("open tickets differ")
    if (old.get("skip_reason_counts") or {}) != (new.get("skip_reason_counts") or {}):
        problems.append(f"skip counts: {_diff(old.get('skip_reason_counts') or {}, new.get('skip_reason_counts') or {})}")
    return problems


def compare_ledger(closed: Sequence[dict[str, Any]], ledger_trades: Sequence[dict[str, Any]]) -> list[str]:
    """Each filled paper trade is one CLOSED ledger trade: same qty, exit time, prices within a tick."""
    problems: list[str] = []
    rows = {t["trade_id"]: t for t in ledger_trades}
    filled = [r for r in closed if r.get("filled")]
    n_ledger = sum(1 for t in rows.values() if t["status"] == "CLOSED")
    if n_ledger != len(filled):
        problems.append(f"ledger CLOSED trades {n_ledger} vs paper filled {len(filled)}")
    for r in filled:
        t = rows.get(r["trade_id"])
        if t is None or t["status"] != "CLOSED":
            problems.append(f"{r['trade_id']}: not CLOSED in ledger")
            continue
        exit_time = datetime.fromtimestamp(int(r["closed_ts"]), IST).isoformat(timespec="seconds")
        checks = {
            "qty": (t["entry_qty"] == r["qty"] == t["exit_qty"]),
            "entry_price": abs(float(t["entry_price"]) - float(r["entry"])) <= PRICE_TOL,
            "exit_price": abs(float(t["exit_price"]) - float(r["exit"])) <= PRICE_TOL,
            "exit_time": t["exit_time"] == exit_time,
        }
        bad = [k for k, ok in checks.items() if not ok]
        if bad:
            problems.append(f"{r['trade_id']}: ledger {bad} ({t['entry_price']}/{t['exit_price']} vs {r['entry']}/{r['exit']})")
    return problems


def summarize(closed: Iterable[dict[str, Any]]) -> dict[str, Any]:
    filled = [r for r in closed if r.get("filled")]
    return {
        "n_trades": len(filled),
        "net_pnl_inr": round(sum(float(r.get("realized_pnl_inr") or 0.0) for r in filled), 2),
        "gross_pnl_inr": round(sum(float(r.get("gross_pnl_inr") or 0.0) for r in filled), 2),
    }


def run_parity(**replay_kw: Any) -> dict[str, Any]:
    """Replay once per path with identical kwargs and compare. `write` is forced off."""
    from desk_ml.event_path import EventSession
    from desk_ml.paper_scalp import replay_paper_scalp

    kw = {**replay_kw, "write": False}
    old = replay_paper_scalp(**kw, use_event_bus=False)
    session = EventSession()
    try:
        new = replay_paper_scalp(**kw, event_session=session)
        problems = compare_boards(old, new)
        problems += compare_ledger(new.get("closed_trades") or [], session.ledger_trades())
        bus = new.get("event_bus") or {}
        if bus.get("handler_errors"):
            problems.append(f"event handler errors: {bus['handler_errors'][:3]}")
    finally:
        session.close()
    return {
        "ok": not problems,
        "problems": problems,
        "old": summarize(old.get("closed_trades") or []),
        "new": summarize(new.get("closed_trades") or []),
        "event_bus": bus,
        "closed_trades": new.get("closed_trades") or [],
    }


# ------------------------------------------------------------------ fixtures


SYNTHETIC_SHAPE = {"NIFTY": (25000.0, 1.0, 50, 200), "SENSEX": (80000.0, 3.2, 100, 300)}  # base, scale, step, ITM


def synthetic_triples(
    *, day: str = "2026-09-10", seed: int = 23, step_s: int = 20, underlying: str = "NIFTY"
) -> list[Triple]:
    """Deterministic session: random-walk index with regime drift, deep-ITM premiums. Not market data."""
    base, k, step, itm = SYNTHETIC_SHAPE[underlying.upper()]
    rng = random.Random(seed)
    y, m, d = (int(p) for p in day.split("-"))
    t0 = int(datetime(y, m, d, 9, 15, tzinfo=IST).timestamp())
    t1 = int(datetime(y, m, d, 15, 30, tzinfo=IST).timestamp())
    idx, drift, out = base, 0.0, []
    for ts in range(t0, t1 + 1, step_s):
        if rng.random() < 0.01:
            drift = rng.choice([-1.2, -0.6, 0.0, 0.0, 0.6, 1.2])
        idx += drift * k + rng.gauss(0, 3.0 * k)
        atm = round(idx / step) * step
        out.append(Triple(
            ts=ts, idx_close=round(idx, 2),
            ce_close=round(max(0.05, max(0.0, idx - atm) + 60.0), 2),
            pe_close=round(max(0.05, max(0.0, atm - idx) + 60.0), 2),
            atm_strike=float(atm),
            itm_ce_close=round(max(0.0, idx - (atm - itm)) + 40.0, 2),
            itm_pe_close=round(max(0.0, (atm + itm) - idx) + 40.0, 2),
            itm_ce_strike=float(atm - itm), itm_pe_strike=float(atm + itm),
            idx_volume=float(1000 + rng.randint(0, 500)), premium_kind="ITM",
        ))
    return out


def write_fixture(path: Path, *, day: str = "2026-09-10", seed: int = 23) -> None:
    rows = [[getattr(t, f) for f in TRIPLE_FIELDS] for t in synthetic_triples(day=day, seed=seed)]
    blob = {"note": "Synthetic NIFTY session for event-bus parity. Not market data.", "underlying": "NIFTY",
            "session_ist_date": day, "seed": seed, "lot_size": 65, "fields": list(TRIPLE_FIELDS), "rows": rows}
    Path(path).write_text(json.dumps(blob, separators=(",", ":")) + "\n", encoding="utf-8")


def load_fixture(path: Path) -> dict[str, Any]:
    blob = json.loads(Path(path).read_text(encoding="utf-8"))
    triples = [Triple(**dict(zip(blob["fields"], row))) for row in blob["rows"]]
    return {**blob, "triples": triples}


def fixture_replay_kwargs(fx: dict[str, Any], root: Path) -> dict[str, Any]:
    """Replay kwargs for a fixture in an isolated root (founder book: this index tradable)."""
    from desk_ml.founder_session import save_founder_book

    save_founder_book([fx["underlying"]], root=root)
    return {"root": root, "underlyings": (fx["underlying"],), "triples_by_und": {fx["underlying"]: fx["triples"]},
            "session_ist_date": fx["session_ist_date"]}


def run_fixture_parity(path: Path) -> dict[str, Any]:
    """No prior-day closes and a fixed lot size, so the fixture never reads repo data."""
    import desk_ml.paper_scalp as ps

    fx = load_fixture(path)
    saved = ps.load_index_closes, ps.resolve_lot_size
    ps.load_index_closes = lambda u, root=None: {}
    ps.resolve_lot_size = lambda und, root=None: (int(fx["lot_size"]), "fixture")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            return run_parity(**fixture_replay_kwargs(fx, Path(tmp)))
    finally:
        ps.load_index_closes, ps.resolve_lot_size = saved


# ----------------------------------------------------------------------- CLI


def _kw(items: Sequence[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items:
        key, _, raw = item.partition("=")
        try:
            out[key] = json.loads(raw)
        except json.JSONDecodeError:
            out[key] = raw
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m desk_ml.event_parity", description=__doc__.split("\n\n")[0])
    ap.add_argument("--fixture", type=Path, help="synthetic fixture JSON (instead of recorded days)")
    ap.add_argument("--root", type=Path, help="repo root with data/recon (default: this checkout)")
    ap.add_argument("--since", default="2026-09-17")
    ap.add_argument("--until", default="2026-09-25")
    ap.add_argument("--days", nargs="*", help="explicit IST dates (overrides --since/--until)")
    ap.add_argument("--underlyings", nargs="*", default=["NIFTY"])
    ap.add_argument("--source", default="dual-tape")
    ap.add_argument("--no-live-session", action="store_true", help="historical replay instead of live-session params")
    ap.add_argument("--kw", action="append", default=[], metavar="KEY=JSON", help="extra replay_paper_scalp kwarg")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args(argv)

    if args.fixture:
        reports = {"fixture": run_fixture_parity(args.fixture)}
    else:
        from desk_ml.paper_scalp import list_fix_first_days
        from desk_ml.persist import repo_root

        root = args.root or repo_root()
        days = args.days or [d for d in list_fix_first_days(root=root, since=args.since) if d <= args.until]
        if not days:
            print(f"no dual-tape days in {root}/data/recon/paper_watch/DUAL-TAPE for {args.since}..{args.until}")
            return 1
        reports = {
            day: run_parity(root=root, underlyings=tuple(args.underlyings), source=args.source,
                            live_session=not args.no_live_session, session_ist_date=day, **_kw(args.kw))
            for day in days
        }
    total_old = {"n_trades": 0, "net_pnl_inr": 0.0}
    total_new = {"n_trades": 0, "net_pnl_inr": 0.0}
    for day, rep in reports.items():
        for tot, side in ((total_old, rep["old"]), (total_new, rep["new"])):
            tot["n_trades"] += side["n_trades"]
            tot["net_pnl_inr"] = round(tot["net_pnl_inr"] + side["net_pnl_inr"], 2)
        lat = (rep["event_bus"] or {}).get("latency_p99_ms")
        print(f"{day}: {'PARITY' if rep['ok'] else 'MISMATCH'} old {rep['old']} new {rep['new']} p99_ms {lat}")
        for p in rep["problems"][:10]:
            print(f"    {p}")
    ok = all(r["ok"] for r in reports.values())
    print(f"TOTAL old {total_old} new {total_new} -> {'PARITY' if ok else 'MISMATCH'}")
    if args.json:
        print(json.dumps({d: {k: v for k, v in r.items() if k != "closed_trades"} for d, r in reports.items()},
                         indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
