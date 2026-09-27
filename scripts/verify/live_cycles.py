#!/usr/bin/env python3
"""Offline live-loop emulation on a recorded day: does a later cycle rewrite earlier booked trades?

Copies the day's tape into a scratch root prefix by prefix (the source root is only read), runs one
live cycle per cut-off, optionally toggles founder STOP/START mid-day, and counts history-rewrite
violations (a trade closed by cycle k missing or changed in any later cycle). Runs on main (the
legacy loop: replay_paper_scalp(write=True, live_session=True) every cycle) and on the PR head
(desk_ml.live_cycle.run_cycle), so the before/after is one command on each tree.

    python scripts/verify/live_cycles.py --root $R --day 2026-09-25 --underlyings NIFTY \\
        --every 10 --founder-stop 12:30 --out out/live_0925_founder.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
KEYS = ("trade_id", "entry", "exit", "exit_reason", "closed_ts", "opened_ts", "realized_pnl_inr", "filled", "qty")
COPY = ("founder_trade_underlyings.json", "ml_paper_session_params.json", "optidx_lot_cache.json")


def ts_at(day: str, hhmm: str) -> int:
    y, m, d = (int(p) for p in day.split("-"))
    hh, mm = (int(p) for p in hhmm.split(":"))
    return int(datetime(y, m, d, hh, mm, tzinfo=IST).timestamp())


def parse_ts(raw) -> int | None:
    try:
        return int(datetime.fromisoformat(str(raw)).timestamp())
    except (TypeError, ValueError):
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, required=True, help="data root holding the recorded tape (read only)")
    ap.add_argument("--day", required=True)
    ap.add_argument("--underlyings", nargs="*", default=["NIFTY"])
    ap.add_argument("--every", type=int, default=10, help="minutes between cycles")
    ap.add_argument("--start", default="09:30")
    ap.add_argument("--end", default="15:30")
    ap.add_argument("--founder-stop", default=None, help="HH:MM: STOP every listed index")
    ap.add_argument("--founder-start", default=None, help="HH:MM: START them again")
    ap.add_argument("--flag-on", action="store_true", help="USE_EVENT_BUS path")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    import desk_ml.founder_session as fs
    import desk_ml.paper_scalp as ps

    try:
        from desk_ml.live_cycle import run_cycle
    except ImportError:  # main: the legacy live loop
        run_cycle = None
    src = args.root / "data" / "recon" / "paper_watch" / "DUAL-TAPE" / f"{args.day}.jsonl"
    lines = [(parse_ts((json.loads(ln) or {}).get("as_of_ist")) or 0, ln) for ln in src.read_text().splitlines() if ln.strip()]
    scratch = Path(tempfile.mkdtemp(prefix="live_cycles_"))
    recon = scratch / "data" / "recon"
    (recon / "paper_watch" / "DUAL-TAPE").mkdir(parents=True)
    for name in COPY:
        if (args.root / "data" / "recon" / name).is_file():
            shutil.copy(args.root / "data" / "recon" / name, recon / name)
    if (args.root / "data" / "recon" / "ohlc").is_dir():
        (recon / "ohlc").symlink_to((args.root / "data" / "recon" / "ohlc").resolve())
    events = []
    if args.founder_stop:
        events.append((ts_at(args.day, args.founder_stop), "STOP"))
    if args.founder_start:
        events.append((ts_at(args.day, args.founder_start), "START"))
    cut, stop_at = ts_at(args.day, args.start), ts_at(args.day, args.end)
    cycles, done = [], set()
    while cut <= stop_at:
        (recon / "paper_watch" / "DUAL-TAPE" / f"{args.day}.jsonl").write_text(
            "".join(ln + "\n" for t, ln in lines if t <= cut))
        for when, action in events:
            if when <= cut and when not in done:
                done.add(when)
                for und in args.underlyings:
                    if run_cycle is not None:
                        fs.set_index_trade(und, action, root=scratch, ts=float(when))
                    else:
                        fs.set_index_trade(und, action, root=scratch)
        kw = dict(deny_model_signals=True, nifty_cover_closed_1m=True, use_event_bus=bool(args.flag_on))
        if run_cycle is not None:
            now = datetime.fromtimestamp(cut + 2, IST)
            board = run_cycle(scratch, underlyings=tuple(args.underlyings), source="dual-tape",
                              clock=lambda now=now: now, session_ist_date=args.day, replay_kw=kw)
        else:
            board = ps.replay_paper_scalp(root=scratch, underlyings=tuple(args.underlyings), source="dual-tape",
                                          write=True, live_session=True, session_ist_date=args.day, **kw)
        closed = [{k: r.get(k) for k in KEYS} for r in board.get("closed_trades") or []]
        cycles.append({"cutoff": cut, "hhmm": datetime.fromtimestamp(cut, IST).strftime("%H:%M"), "closed": closed})
        print(f"{cycles[-1]['hhmm']}: {sum(1 for r in closed if r['filled'])} filled, "
              f"net {round(sum(float(r['realized_pnl_inr'] or 0) for r in closed if r['filled']), 2):,.2f}")
        cut += args.every * 60
    violations = []
    for i, a in enumerate(cycles):
        booked = {r["trade_id"]: r for r in a["closed"] if int(r["closed_ts"] or 0) <= a["cutoff"]}
        for b in cycles[i + 1:]:
            later = {r["trade_id"]: r for r in b["closed"]}
            for tid, row in booked.items():
                if later.get(tid) != row:
                    violations.append({"closed_by": a["hhmm"], "seen_at": b["hhmm"], "trade_id": tid, "was": row,
                                       "now": later.get(tid)})
    stop_ts = events[0][0] if events else None
    kept = [r for r in cycles[-1]["closed"] if stop_ts and r["filled"] and int(r["closed_ts"]) < stop_ts]
    report = {"tree": "pr-head (live_cycle)" if run_cycle else "main (legacy loop)", "day": args.day,
              "history_rewrite_violations": len(violations), "examples": violations[:5],
              "booked_before_stop_at_end": {"n": len(kept), "net": round(sum(float(r["realized_pnl_inr"] or 0) for r in kept), 2)},
              "cycles": [{"hhmm": c["hhmm"], "n_closed": len(c["closed"])} for c in cycles]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, default=str))
    print(f"{report['tree']}: {len(violations)} history-rewrite violation(s); "
          f"booked before the STOP at end of day: {report['booked_before_stop_at_end']}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
