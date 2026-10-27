"""Read-only pull of Dhan expired/rolling index options (POST /charts/rollingoption), founder OK 2026-10-27.
https://dhanhq.co/docs/v2/expired-options-data/ : 1m OHLC+OI+IV+spot, ATM-relative strikes, <=30 days/call,
Data API 5 req/s (enforced by dhan_client), 100k/day. No orders. Token from .env via dhan_client; never printed.

Run with the v2 venv (dhan_client needs py3.11):
  .venv-v2/bin/python scripts/lab5y/pull_expired.py --from 2025-10-27 --to 2026-10-27 [--test]
Output: data/cache/expired_opts/<SYM>/<ATM+k>_<CALL|PUT>_<from>.json (gitignored); existing files are skipped."""
import argparse, json, sys, time
from datetime import date, timedelta
from pathlib import Path

from dhan_client.client import DhanClient

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "cache" / "expired_opts"
UND = {"NIFTY": ("NSE_FNO", 13), "SENSEX": ("BSE_FNO", 51)}
FIELDS = ["open", "high", "low", "close", "iv", "volume", "strike", "oi", "spot"]


def windows(a: date, b: date, days: int = 30):
    while a < b:
        yield a, min(a + timedelta(days=days), b)
        a += timedelta(days=days)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="a", required=True)
    ap.add_argument("--to", dest="b", required=True)
    ap.add_argument("--strikes", type=int, default=3)
    ap.add_argument("--test", action="store_true", help="one call (NIFTY ATM CALL, first window) and a summary")
    ns = ap.parse_args()
    cli = DhanClient(dry_run=False)
    jobs = [(s, k, side, w) for s in UND for k in range(-ns.strikes, ns.strikes + 1)
            for side in ("CALL", "PUT") for w in windows(date.fromisoformat(ns.a), date.fromisoformat(ns.b))]
    if ns.test:
        jobs = [j for j in jobs if j[0] == "NIFTY" and j[1] == 0 and j[2] == "CALL"][:1]
    done = err = 0
    for sym, k, side, (fa, fb) in jobs:
        strike = "ATM" if k == 0 else f"ATM{k:+d}"
        fp = OUT / sym / f"{strike}_{side}_{fa}.json"
        if fp.exists() and not ns.test:
            continue
        seg, sid = UND[sym]
        body = dict(exchangeSegment=seg, interval="1", securityId=sid, instrument="OPTIDX", expiryFlag="WEEK",
                    expiryCode=1, strike=strike, drvOptionType=side, requiredData=FIELDS,
                    fromDate=fa.isoformat(), toDate=fb.isoformat())
        try:
            r = cli.historical.rolling_option(body)
        except Exception as e:  # keep going; message is a code, never a secret
            err += 1
            print(f"ERR {sym} {strike} {side} {fa}: {type(e).__name__}: {str(e)[:160]}", flush=True)
            time.sleep(1)
            continue
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(r))
        done += 1
        if ns.test:
            d = (r.get("data") or {}).get("ce" if side == "CALL" else "pe") or {}
            print("keys:", sorted(d), "| bars:", len(d.get("timestamp") or []))
            for f in ("timestamp", "close", "oi", "iv", "spot", "strike"):
                v = d.get(f) or []
                print(f, v[:2], "...", v[-2:])
        elif done % 25 == 0:
            print(f"{done} saved, {err} errors", flush=True)
    print(f"done: {done} saved, {err} errors, {len(jobs)} jobs", flush=True)
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
