"""Cache option tape (quote_snapshots + index/futures from depth) into compact per-day parquet.
Streams depth_quotes.jsonl line by line; keeps only index + futures rows, 1 row/sec/instrument.
Usage: ~/paper_extra_venv/bin/python scripts/lab5y/tape_cache.py OUTDIR
"""
import json, sys, os, glob
import pandas as pd

TAPE = os.path.join(os.path.dirname(__file__), "../../data/tape/v2")
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

def quotes(day):
    rows = []
    with open(f"{TAPE}/{day}/quote_snapshots.jsonl") as f:
        for ln in f:
            try: e = json.loads(ln)
            except Exception: continue
            p = e["payload"]; rows.append((e["timestamp"][:19], p["instrument_id"], p.get("rule"), p.get("side"),
                         p.get("bid"), p.get("ask"), p.get("ltp"), p.get("oi"), p.get("stale")))
    df = pd.DataFrame(rows, columns="ts iid rule side bid ask ltp oi stale".split())
    df["ts"] = pd.to_datetime(df["ts"]); return df

def depth_under(day):
    # index (NSE_IDX / BSE_IDX) and futures (exchange:SYM:YYYY-MM-DD with 3 parts); last row per second
    last = {}
    with open(f"{TAPE}/{day}/depth_quotes.jsonl") as f:
        for ln in f:
            i = ln.find('"instrument_id":"'); j = ln.find('"', i + 17); iid = ln[i + 17:j]
            if not ("_IDX:" in iid or iid.count(":") == 2): continue
            e = json.loads(ln); p = e["payload"]; ts = (p.get("exchange_ts") or e["timestamp"])[:19]
            lv = p.get("levels") or {}
            bq = sum(q for _, q in lv.get("bid", [])) if lv.get("bid") else None
            aq = sum(q for _, q in lv.get("ask", [])) if lv.get("ask") else None
            last[(iid, ts)] = (ts, iid, p.get("ltp"), p.get("bid"), p.get("ask"), p.get("bid_qty"), p.get("ask_qty"), bq, aq, p.get("oi"))
    df = pd.DataFrame(list(last.values()), columns="ts iid ltp bid ask bq1 aq1 bq5 aq5 oi".split())
    df["ts"] = pd.to_datetime(df["ts"]); return df

for d in sorted(os.listdir(TAPE)):
    if d == "2026-10-27": continue
    if not os.path.exists(f"{OUT}/{d}_u.parquet"):
        quotes(d).to_parquet(f"{OUT}/{d}_q.parquet"); depth_under(d).to_parquet(f"{OUT}/{d}_u.parquet"); print(d, flush=True)


def depth_opts(day):
    """all option instruments from depth (instruments leave quote_snapshots when ATM rolls; depth keeps them):
    first row in each 5s bucket -> bid, ask, oi."""
    seen = set(); rows = []
    with open(f"{TAPE}/{day}/depth_quotes.jsonl") as f:
        for ln in f:
            i = ln.find('"instrument_id":"'); j = ln.find('"', i + 17); iid = ln[i + 17:j]
            if iid.count(":") != 4: continue
            t = ln.find('"exchange_ts":"'); ts = ln[t + 15:t + 34] if t > 0 else None
            if not ts or ts[0] != "2": continue
            b = (iid, ts[:17] + str(int(ts[17:19]) // 5 * 5).zfill(2))
            if b in seen: continue
            seen.add(b); p = json.loads(ln)["payload"]
            rows.append((b[1], iid, p.get("bid"), p.get("ask"), p.get("oi")))
    df = pd.DataFrame(rows, columns="ts iid bid ask oi".split()); df["ts"] = pd.to_datetime(df["ts"]); return df


if __name__ == "__main__":
    for d in sorted(os.listdir(TAPE)):
        if d != "2026-10-27" and not os.path.exists(f"{OUT}/{d}_o.parquet"):
            depth_opts(d).to_parquet(f"{OUT}/{d}_o.parquet"); print("opt", d, flush=True)
