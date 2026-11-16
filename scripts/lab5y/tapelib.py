"""Tick-tape library shared by scalp_lab (E46) and expiry_bot (E50): the per-day tick cache, 100 ms as-of grids, the frozen
E46 fill model (two-level market walk, resting target, stop + 500 ms latency, time-out, passive queue) and real charges.
Paper research only; reads data/tape/v2, no broker calls. Extracted verbatim from scalp_lab.py on 2026-11-16 so that
expiry_bot can import it without loading the 5-year panel that scalp_lab needs."""
import os, numpy as np, pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
TAPE = os.environ.get("TAPE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/tape/v2"))
TAPEC = os.environ.get("TAPEC", os.path.join(_HERE, "../../data/cache/tapetick"))
TAPE_DAYS = ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19", "2026-10-21", "2026-10-22", "2026-10-28", "2026-10-29", "2026-11-13"]


def study_tapecache(days=None):
    """depth_quotes.jsonl -> one parquet per day with EVERY non-repeat tick of every instrument (index, futures, options):
    t = receipt time in ms since midnight IST (what the desk could know), xt = exchange time, best bid/ask + sizes, 5-level size sums,
    second-level prices, ltp, oi. Read-only on the tape; no broker calls."""
    import json
    os.makedirs(TAPEC, exist_ok=True)
    ms = lambda z: (int(z[11:13]) * 3600 + int(z[14:16]) * 60 + int(z[17:19])) * 1000 + (int(z[20:23]) if len(z) > 20 and z[19] == "." else 0)
    for day in (days or TAPE_DAYS):
        out = f"{TAPEC}/{day}.parquet"
        if os.path.exists(out): continue
        rows = []
        with open(f"{TAPE}/{day}/depth_quotes.jsonl") as f:
            for ln in f:
                if '"repeat":true' in ln: continue
                try: e = json.loads(ln)
                except Exception: continue
                p = e["payload"]; lv = p.get("levels") or {}; b, a = lv.get("bid") or [], lv.get("ask") or []; xt = p.get("exchange_ts") or e["timestamp"]
                rows.append((ms(e["timestamp"]), ms(xt), p["instrument_id"], p.get("bid"), p.get("ask"), p.get("bid_qty"), p.get("ask_qty"), p.get("ltp"), p.get("oi"),
                             sum(q for _, q in b) if b else None, sum(q for _, q in a) if a else None, b[1][0] if len(b) > 1 else None, a[1][0] if len(a) > 1 else None))
        df = pd.DataFrame(rows, columns="t xt iid bid ask bq aq ltp oi b5 a5 bid2 ask2".split()); df["iid"] = df.iid.astype("category")
        df.to_parquet(out); print(day, len(df), df.iid.nunique(), flush=True)


T0MS, NSLOT, LAT = 33_300_000, 225_001, 5   # grid: 100 ms slots from 09:15:00 to 15:30:00; LAT = 500 ms in slots
DISC = TAPE_DAYS[:8]; HOLD = TAPE_DAYS[8:]
TSYM = {"NIFTY": dict(pre="NSE_FNO:NIFTY", idx="NSE_IDX:NIFTY", step=50, q=650, m=1.0, cap=0.20, tx=0.000355299),
        "SENSEX": dict(pre="BSE_FNO:SENSEX", idx="BSE_IDX:SENSEX", step=100, q=200, m=3.0, cap=3.00, tx=0.000325)}
if os.environ.get("TCAP"): TSYM["NIFTY"]["cap"] = float(os.environ["TCAP"])  # post-hoc sensitivity only (E46 froze 0.20, which drops ~85% of NIFTY non-expiry moments)
GCOLS = ["bid", "ask", "bq", "aq", "ltp", "b5", "a5", "bid2", "ask2"]
slot_of = lambda t: np.ceil((np.asarray(t) - T0MS) / 100).astype(int)   # first grid slot whose as-of state includes a tick received at t


class TapeDay:
    """one day's ticks: per-instrument tick arrays and lazily built 100 ms as-of grids (state at a slot = the latest tick received <= slot time)."""
    def __init__(self, day):
        df = pd.read_parquet(f"{TAPEC}/{day}.parquet"); df = df[(df.t >= T0MS) & (df.t <= T0MS + (NSLOT - 1) * 100)].sort_values("t", kind="stable")
        self.day = day; self.ticks = {k: g for k, g in df.groupby(df.iid.astype(str), sort=False)}; self._g = {}
        fut = [k for k in self.ticks if k.count(":") == 2 and k.startswith("NSE_FNO:NIFTY")]; self.fut = min(fut, key=lambda k: k.split(":")[2]) if fut else None
        self.exp = {}
        for sym, c in TSYM.items():
            ex = sorted({k.split(":")[2] for k in self.ticks if k.count(":") == 4 and k.startswith(c["pre"] + ":") and k.split(":")[2] >= day})
            self.exp[sym] = ex[0] if ex else None

    def grid(self, iid):
        if iid not in self._g:
            g = self.ticks.get(iid)
            if g is None: self._g[iid] = None
            else:
                t = g.t.values; st = T0MS + np.arange(NSLOT) * 100; ix = np.searchsorted(t, st, "right") - 1; ok = ix >= 0; ix = np.maximum(ix, 0)
                G = {c: np.where(ok, g[c].values[ix], np.nan).astype(np.float32) for c in GCOLS}; G["age"] = np.where(ok, st - t[ix], 1e9)
                G["mid"] = (G["bid"] + G["ask"]) / 2; self._g[iid] = G
        return self._g[iid]

    def atm(self, sym):
        """ATM strike per slot from the cash index ltp (as-of)."""
        c = TSYM[sym]; G = self.grid(c["idx"]); return None if G is None else np.round(G["ltp"] / c["step"]) * c["step"]

    def oid(self, sym, K, side): return f"{TSYM[sym]['pre']}:{self.exp[sym]}:{int(K)}:{side}"


def _valid(G, s, cap):
    with np.errstate(invalid="ignore"): return (G["age"][s] <= 1500) & (G["bid"][s] > 0) & (G["ask"][s] > G["bid"][s] - 1e-9) & (G["ask"][s] - G["bid"][s] <= cap + 1e-6)


def _walk(G, s, q, buy):
    """market fill for q units at slot s: the best size at the best price, the rest at the second-level price (tick 0.05 beyond if missing)."""
    p1, z1, p2 = (G["ask"][s], G["aq"][s], G["ask2"][s]) if buy else (G["bid"][s], G["bq"][s], G["bid2"][s])
    p1 = p1.astype(float); p2 = np.where(np.isfinite(p2), p2, p1 + (0.05 if buy else -0.05)).astype(float); z1 = np.nan_to_num(z1.astype(float))
    return np.where(z1 >= q, p1, (z1 * p1 + (q - z1) * p2) / q)


def _tcharge(b, s_, q, tx):
    """round-trip charges per unit at today's real rates (x1.0): brokerage Rs 20 x 2 orders, exchange, SEBI, GST on those, stamp on the buy, STT on the sale."""
    x = 40 / q + tx * (b + s_) + 1e-6 * (b + s_); return 1.18 * x + 0.00003 * b + 0.0015 * s_


def tsim(G, dec, T, S, H, q, tx, entry="market", short=False, fillmode="queue"):
    """simulate one-leg scalps on one instrument's grid. dec = decision slots. Returns dict of arrays (len(dec)):
    filled, pe (entry price), out (0 target / 1 stop / 2 time-out / -1 no entry), pts (after spread), net (after charges, per unit),
    hs (mid - passive price at posting), e (entry slot), mid0 (mid at decision + latency), cmove (mid move at cancel for non-fills)."""
    dec = np.asarray(dec); N = len(dec); sw = np.lib.stride_tricks.sliding_window_view; p0 = dec + LAT; mid0 = G["mid"][p0].astype(float)
    cmove = np.full(N, np.nan)
    if entry == "market":
        pe = _walk(G, p0, q, not short); e = p0.copy(); filled = np.isfinite(pe); hs = np.abs(pe - mid0)
    else:  # passive long: join the best bid at p0, queue ahead = displayed size, cancel after 10 s (+ latency)
        W = 100 + LAT + 1; pr = G["bid"][p0].astype(float); qa = np.nan_to_num(G["bq"][p0].astype(float)); r = np.arange(N)
        B = sw(G["bid"], W)[p0]; A = sw(G["ask"], W)[p0]; Z = sw(G["bq"], W)[p0]; Lt = sw(G["ltp"], W)[p0]
        with np.errstate(invalid="ignore"):
            thr = (A[:, 1:] <= pr[:, None]) | (B[:, 1:] < pr[:, None])
            strict = (A[:, 1:] <= pr[:, None]) | ((Lt[:, 1:] < pr[:, None]) & (Lt[:, 1:] != Lt[:, :-1]))
            same = (B[:, 1:] == pr[:, None]) & (B[:, :-1] == pr[:, None]) & (Lt[:, 1:] == pr[:, None]); drop = np.where(same, np.maximum(Z[:, :-1] - Z[:, 1:], 0), 0)
        hitq = np.cumsum(np.nan_to_num(drop), 1) >= (qa + q)[:, None]
        hit = {"queue": thr | hitq, "through": thr, "strict": strict}[fillmode]; filled = hit.any(1); j = hit.argmax(1) + 1
        e = np.where(filled, p0 + j, p0); pe = np.where(filled, pr, np.nan); hs = mid0 - pr; cmove = np.where(filled, np.nan, G["mid"][p0 + W - 1] - mid0)
    out = np.full(N, -1); pts = np.full(N, np.nan); net = np.full(N, np.nan); f = np.flatnonzero(filled)
    if len(f):
        ef = e[f]; M = sw(G["mid"], H + 1)[ef][:, 1:]; pf = pe[f]
        with np.errstate(invalid="ignore"):
            if short: Q_ = sw(G["ask"], H + LAT + 1)[ef][:, 1:]; st = M >= (pf + S)[:, None]; tg = Q_ <= (pf - T)[:, None]
            else: Q_ = sw(G["bid"], H + LAT + 1)[ef][:, 1:]; st = M <= (pf - S)[:, None]; tg = Q_ >= (pf + T)[:, None]
        si = np.where(st.any(1), st.argmax(1) + 1, 10 ** 9); ti = np.where(tg.any(1), tg.argmax(1) + 1, 10 ** 9)
        o = np.where(si <= np.minimum(ti, H), 1, np.where(ti <= H + LAT, 0, 2)); xs = ef + np.where(o == 1, si, H) + LAT
        xp = np.where(o == 0, pf + (-T if short else T), _walk(G, np.minimum(xs, NSLOT - 1), q, short))
        g = (pf - xp) if short else (xp - pf); c = _tcharge(xp, pf, q, tx) if short else _tcharge(pf, xp, q, tx)
        out[f] = o; pts[f] = g; net[f] = g - c
    return dict(filled=filled, pe=pe, out=out, pts=pts, net=net, hs=hs, e=e, mid0=mid0, cmove=cmove)


def _atm_decisions(TD, sym, dec):
    """(instrument id, decision slots) for the ATM CE and PE at each decision slot, valid quotes only, with room for the longest hold."""
    c = TSYM[sym]; atm = TD.atm(sym); out = {}
    if atm is None or TD.exp[sym] is None: return out
    for K in np.unique(atm[dec][np.isfinite(atm[dec])]):
        for side in ("CE", "PE"):
            iid = TD.oid(sym, K, side); G = TD.grid(iid)
            if G is None: continue
            s = dec[atm[dec] == K]; s = s[_valid(G, s, c["cap"])]
            if len(s): out[(iid, side)] = s
    return out


