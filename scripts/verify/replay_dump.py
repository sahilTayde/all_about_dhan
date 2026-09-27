#!/usr/bin/env python3
"""Offline legacy replay: per-day canonical trade dumps + sha256, for before/after comparison.

Runs on ``main`` and on the PR head alike (no PR-only imports), so the sha256 of each day must
match between the two trees. Paper only, write=False: nothing is written to the data root.

    # NIFTY with the box founder file, flag off
    python scripts/verify/replay_dump.py --root $R --since 2026-09-17 --until 2026-09-25 --out out/nifty_off
    # same, flag on (event path with the replay risk file, exactly as desk_ml.event_parity runs it)
    python scripts/verify/replay_dump.py --root $R ... --flag-on --out out/nifty_on
    # all 3 indices, founder all-START in process (no founder file needed)
    python scripts/verify/replay_dump.py --root $R --underlyings NIFTY BANKNIFTY SENSEX --all-start ...

``$R`` is a scratch data root (data/recon/paper_watch/DUAL-TAPE/*.jsonl, founder JSON, params JSON,
lot cache), e.g. built by the box's mkroot.sh. Extra replay kwargs: ``--kw key=<json>``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

TRADE_KEYS = (
    "trade_id", "book_id", "underlying", "side", "atm_strike", "opened_ts", "closed_ts", "entry", "exit", "qty",
    "lots", "exit_reason", "gross_pnl_inr", "charges_inr", "realized_pnl_inr", "filled",
)


def _num(v):
    return round(v, 6) if isinstance(v, float) else v


def canonical(board: dict) -> bytes:
    closed = sorted(({k: _num(r.get(k)) for k in TRADE_KEYS} for r in board.get("closed_trades") or []),
                    key=lambda r: (str(r["underlying"]), int(r["opened_ts"] or 0), str(r["trade_id"])))
    blob = {"closed_trades": closed, "skip_reason_counts": board.get("skip_reason_counts") or {}}
    return (json.dumps(blob, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--since", default="2026-09-17")
    ap.add_argument("--until", default="2026-09-25")
    ap.add_argument("--days", nargs="*")
    ap.add_argument("--underlyings", nargs="*", default=["NIFTY"])
    ap.add_argument("--all-start", action="store_true", help="founder allow-all in process (box ALL3 config)")
    ap.add_argument("--flag-on", action="store_true", help="event path (EventSession, replay risk file)")
    ap.add_argument("--kw", action="append", default=[], metavar="KEY=JSON")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    import desk_ml.founder_session as fs
    from desk_ml.paper_scalp import replay_paper_scalp

    if args.all_start:
        fs.allows_new_fill = lambda underlying, root=None: True
    folder = args.root / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    days = args.days or sorted(p.stem for p in folder.glob("*.jsonl") if args.since <= p.stem <= args.until)
    kw = {}
    for item in args.kw:
        key, _, raw = item.partition("=")
        try:
            kw[key] = json.loads(raw)
        except json.JSONDecodeError:
            kw[key] = raw
    args.out.mkdir(parents=True, exist_ok=True)
    total_n, total_net, manifest = 0, 0.0, {}
    for day in days:
        session = None
        if args.flag_on:
            from desk_ml.event_path import EventSession

            session = EventSession()
            kw["event_session"] = session
        try:
            board = replay_paper_scalp(root=args.root, underlyings=tuple(args.underlyings), source="dual-tape",
                                       write=False, live_session=True, session_ist_date=day, **kw)
        finally:
            if session is not None:
                session.close()
        data = canonical(board)
        (args.out / f"{day}.json").write_bytes(data)
        filled = [r for r in board.get("closed_trades") or [] if r.get("filled")]
        net = round(sum(float(r.get("realized_pnl_inr") or 0) for r in filled), 2)
        total_n += len(filled)
        total_net = round(total_net + net, 2)
        manifest[day] = {"n": len(filled), "net": net, "sha256": hashlib.sha256(data).hexdigest()}
        print(f"{day}: {len(filled)} / {net:,.2f}  sha256 {manifest[day]['sha256'][:16]}")
    manifest["TOTAL"] = {"n": total_n, "net": total_net}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"TOTAL {total_n} / {total_net:,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
