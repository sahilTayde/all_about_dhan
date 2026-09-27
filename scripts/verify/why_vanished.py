#!/usr/bin/env python3
"""Why did a ticket booked in one live cycle not come back in the next? Diff the entry tick's inputs.

Replays the day's tape cut at two times (as two live cycles would see it, write=False) and prints,
for the given index and entry tick, every decision input that differs between the two replays:
logit / XR sides, votes, picker, observer, and the skip reasons recorded at that tick. The source
root is only read. Runs on main and on the PR head.

    python scripts/verify/why_vanished.py --root $R --day 2026-09-21 --underlying NIFTY \\
        --entry 14:09:43 --cut-a 14:10 --cut-b 14:20
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
COPY = ("founder_trade_underlyings.json", "ml_paper_session_params.json", "optidx_lot_cache.json")


def at(day: str, hhmm: str) -> int:
    y, m, d = (int(p) for p in day.split("-"))
    parts = [int(p) for p in hhmm.split(":")] + [0]
    return int(datetime(y, m, d, parts[0], parts[1], parts[2], tzinfo=IST).timestamp())


def capture(args, cut: int) -> dict:
    import desk_ml.paper_scalp as ps

    src = args.root / "data" / "recon" / "paper_watch" / "DUAL-TAPE" / f"{args.day}.jsonl"
    scratch = Path(tempfile.mkdtemp(prefix="why_vanished_"))
    recon = scratch / "data" / "recon"
    (recon / "paper_watch" / "DUAL-TAPE").mkdir(parents=True)
    for name in COPY:
        if (args.root / "data" / "recon" / name).is_file():
            shutil.copy(args.root / "data" / "recon" / name, recon / name)
    if (args.root / "data" / "recon" / "ohlc").is_dir():
        (recon / "ohlc").symlink_to((args.root / "data" / "recon" / "ohlc").resolve())
    keep = [ln for ln in src.read_text().splitlines()
            if ln.strip() and int(datetime.fromisoformat(json.loads(ln)["as_of_ist"]).timestamp()) <= cut]
    (recon / "paper_watch" / "DUAL-TAPE" / f"{args.day}.jsonl").write_text("".join(ln + "\n" for ln in keep))
    target = at(args.day, args.entry)
    seen: dict = {}
    real_decide = ps.step_decide

    def spy(engine, s, votes, **kw):
        out = real_decide(engine, s, votes, **kw)
        if s.und == args.underlying and int(s.tick.ts) == target:
            seen["logit"] = {k: v for k, v in (s.logit or {}).items() if k != "n_3m"}  # bar count grows; not a signal
            seen["logit_xr"] = {k: v for k, v in (s.logit_xr or {}).items() if k != "n_3m"}
            seen["votes"] = [getattr(v, "__dict__", str(v)) for v in votes]
            seen["last_step"] = {k: engine.last_step.get(k) for k in ("picker", "observer", "desk", "dealer")}
            seen["skips"] = [x for x in engine.skips if int(x.get("ts") or 0) == target and x.get("underlying") == args.underlying]
            seen["opened"] = [p.trade_id for p in engine.opens.values() if int(p.opened_ts) == target]
        return out

    ps.step_decide = spy
    try:
        board = ps.replay_paper_scalp(root=scratch, underlyings=(args.underlying,), source="dual-tape", write=False,
                                      live_session=True, session_ist_date=args.day, deny_model_signals=True,
                                      nifty_cover_closed_1m=True)
    finally:
        ps.step_decide = real_decide
    seen["tickets_opened_at_entry"] = [r["trade_id"] for r in (board.get("closed_trades") or []) + (board.get("open_trades") or [])
                                       if int(r.get("opened_ts") or 0) == target]
    seen["tape_last_tick"] = json.loads(keep[-1])["as_of_ist"] if keep else None
    return seen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--day", required=True)
    ap.add_argument("--underlying", default="NIFTY")
    ap.add_argument("--entry", required=True, help="HH:MM:SS of the ticket's entry tick")
    ap.add_argument("--cut-a", required=True, help="HH:MM of the cycle that booked it")
    ap.add_argument("--cut-b", required=True, help="HH:MM of the cycle that lost it")
    args = ap.parse_args(argv)
    a, b = capture(args, at(args.day, args.cut_a)), capture(args, at(args.day, args.cut_b))
    print(f"entry tick {args.entry}: cycle {args.cut_a} opened {a.get('tickets_opened_at_entry')}, "
          f"cycle {args.cut_b} opened {b.get('tickets_opened_at_entry')}")
    for key in sorted(set(a) | set(b)):
        if a.get(key) != b.get(key):
            print(f"\n--- {key} differs\n  {args.cut_a}: {json.dumps(a.get(key), default=str)[:1500]}\n"
                  f"  {args.cut_b}: {json.dumps(b.get(key), default=str)[:1500]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
