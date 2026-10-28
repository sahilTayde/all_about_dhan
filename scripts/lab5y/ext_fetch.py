"""Read-only fetch of public, official daily data that is known before 09:15 IST (round 3: new information sources).
  NSE participant-wise OI (FII/DII/Pro/Client), published after T-1 close:
      https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv
  FRED (St. Louis Fed): SP500 (S&P 500 close), VIXCLS (CBOE VIX close), DEXINUS (INR per USD, noon NY),
  DCOILBRENTEU (Brent spot, EIA). FRED value for US date d-1 is used on Indian day d (fixed before 09:15 IST;
  FRED/EIA publish it later, but the rupee and Brent futures trade live, so a desk would know it).
  F&O bhavcopy (E16/E17), full chain EOD close/OI/volume of every strike, published the evening of the trade date:
      https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip   (NIFTY rows kept)
      https://www.bseindia.com/download/BhavCopy/Derivative/BhavCopy_BSE_FO_0_0_0_YYYYMMDD_F_0000.CSV (SENSEX rows kept)
  GIFT Nifty (E15): no usable source. nseix.com serves history only through a session-token API; not fetched.
No broker API, no orders, no keys. Output: data/cache/ext/ (gitignored); existing NSE files are skipped.
  .venv/bin/python scripts/lab5y/ext_fetch.py 2025-10-01 2026-10-27"""
import sys, io, csv, time, zipfile, urllib.request
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "cache" / "ext"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) research"}


def get(url):  # FRED stalls on browser-like agents; NSE archives reject bare ones
    h = {"User-Agent": "curl/8"} if "fred" in url else UA
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30).read()


BHAV = {"NSE": ("NIFTY", "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{:%Y%m%d}_F_0000.csv.zip"),
        "BSE": ("SENSEX", "https://www.bseindia.com/download/BhavCopy/Derivative/BhavCopy_BSE_FO_0_0_0_{:%Y%m%d}_F_0000.CSV")}
BCOLS = ["TradDt", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "UndrlygPric", "OpnIntrst", "TtlTradgVol"]


def bhav(d):
    """index-option rows of one day's NSE (NIFTY) and BSE (SENSEX) bhavcopy -> data/cache/ext/bhav/{ex}_{d}.csv."""
    n = 0
    for ex, (sym, url) in BHAV.items():
        fp = OUT / "bhav" / f"{ex}_{d}.csv"
        if fp.exists(): continue
        try: raw = get(url.format(d))
        except Exception: continue  # holidays 404
        if raw[:2] == b"PK": raw = zipfile.ZipFile(io.BytesIO(raw)).read(zipfile.ZipFile(io.BytesIO(raw)).namelist()[0])
        R = csv.DictReader(io.StringIO(raw.decode(errors="replace")))
        if "TckrSymb" not in (R.fieldnames or []): continue  # holidays: a 200 page that is not a bhavcopy
        rows = {tuple(r[c] for c in BCOLS) for r in R if r["TckrSymb"] == sym and r["FinInstrmTp"] == "IDO"}  # set: BSE repeats rows
        if not rows: continue
        with open(fp, "w", newline="") as f: w = csv.writer(f); w.writerow(BCOLS); w.writerows(sorted(rows))
        n += 1; time.sleep(0.4)
    return n


def main(a, b):
    (OUT / "nse_poi").mkdir(parents=True, exist_ok=True); (OUT / "bhav").mkdir(exist_ok=True)
    for s in ("SP500", "VIXCLS", "DEXINUS", "DCOILBRENTEU"):
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
        nb = bhav(d) if d.weekday() < 5 else 0; ok += nb
        d += timedelta(days=1)
    print(f"FRED 4 series; NSE participant OI + bhavcopy files saved {ok}, participant OI missing {miss}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
