"""Read-only fetch of public, official daily data that is known before 09:15 IST (round 3: new information sources).
  NSE participant-wise OI (FII/DII/Pro/Client), published after T-1 close:
      https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv
  FRED (St. Louis Fed): SP500 (S&P 500 close), VIXCLS (CBOE VIX close), DEXINUS (INR per USD, noon NY).
No broker API, no orders, no keys. Output: data/cache/ext/ (gitignored); existing NSE files are skipped.
  .venv/bin/python scripts/lab5y/ext_fetch.py 2025-10-01 2026-10-27"""
import sys, time, urllib.request
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "cache" / "ext"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) research"}


def get(url):  # FRED stalls on browser-like agents; NSE archives reject bare ones
    h = {"User-Agent": "curl/8"} if "fred" in url else UA
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30).read()


def main(a, b):
    (OUT / "nse_poi").mkdir(parents=True, exist_ok=True)
    for s in ("SP500", "VIXCLS", "DEXINUS"):
        (OUT / f"{s}.csv").write_bytes(get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}&cosd=2020-01-01"))
    d, ok, miss = date.fromisoformat(a), 0, 0
    while d <= date.fromisoformat(b):
        fp = OUT / "nse_poi" / f"{d}.csv"
        if d.weekday() < 5 and not fp.exists():
            try:
                fp.write_bytes(get(f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{d:%d%m%Y}.csv")); ok += 1
            except Exception:  # holidays 404
                miss += 1
            time.sleep(0.4)
        d += timedelta(days=1)
    print(f"FRED 3 series; NSE participant OI saved {ok}, missing {miss}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
