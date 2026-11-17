"""Daily forward bench (paper research only: reads the recorder tape on disk, never a broker call, never an order).
Founder ask 2026-11-17: test every strategy against the recorder daily, see what works in which situation, learn from it.

After each close: replay every registered cell, FROZEN as registered (never re-tuned here), on that day's tape, tag the day's situation,
append one row per cell per index-day to data/recon/fwd_bench.jsonl, and print "what works where".
  ~/paper_extra_venv/bin/python scripts/lab5y/fwd_bench.py day <YYYY-MM-DD>   # score one taped day, append (a logged day is skipped; --dry prints only; --again fills rows an engine error left out)
  ~/paper_extra_venv/bin/python scripts/lab5y/fwd_bench.py backfill           # every taped day not logged yet (one subprocess per day)
  ~/paper_extra_venv/bin/python scripts/lab5y/fwd_bench.py report [--since D] [--short]
  ~/paper_extra_venv/bin/python scripts/lab5y/fwd_bench.py roster             # what runs, what cannot run on the tape and why
  ~/paper_extra_venv/bin/python scripts/lab5y/fwd_bench.py check <day>        # converter known answer: tape bars vs the Dhan 1m panel on an overlap day
  ~/paper_extra_venv/bin/python scripts/lab5y/fwd_bench.py selftest           # hand-worked known answers (converter, tagger, ledger, report maths); no data needed

Three fill models, each the engine's own, unchanged:
  SH.*   fin1_shadow.day_rows: real bid / ask of the first quote, charges x1.5 (the shadow book: FIN1, S2, S1, SC1, B1, IVS, XS, E33 leads)
  E54.*  expiry_bot.replay_day: tick tape, 500 ms latency, two-level book walk, real charges (expiry days only)
  others the 5-year lab engines (sell_lab.struct and friends: next 1m open +- the p75 half-spread, charges x1.5, COSTS=today) on a panel
         that is the Dhan history up to the day before + THIS day converted from the tape into the panel's own 1m format (`to_bars`).
         The panel never holds a day after the scored one, so no engine can read the future.
Honesty rules: a cell that needs strikes, volume or prior days the tape does not have is logged UNTESTABLE:<why>, never silently skipped
or silently degraded; situation tags used to split results are known at the entry (the or_iv tag only for entries from 09:46);
after-the-fact day types are printed under 'descriptive only'. A day at or before 2026-10-26 is inside the 5-year panel the labs were
already scored on: it is a REPLAY of a seen day on tape prices (seen=true), not out-of-sample; only later days are forward.
Env: FWD_ROOT = the checkout that holds data/ (default: this repo; set it when running from a git worktree), FWD_KEEP=1 keeps the per-day panel.
ponytail: one process and one panel build per day (~2-4 min); ceiling ~250 tape days in the history window, then move HIST_FROM forward."""
import sys, os, json, re, math, shutil, subprocess, tempfile, atexit, traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("FWD_ROOT", HERE.parents[1]))
TAPE, TICK, HIST = ROOT / "data/tape/v2", ROOT / "data/cache/tapetick", ROOT / "data/cache/lab5y_w10"
CACHE = Path(os.environ.get("FWD_CACHE", ROOT / "data/cache/fwd_bench")); LEDGER = Path(os.environ.get("FWD_LEDGER", ROOT / "data/recon/fwd_bench.jsonl"))
HIST_FROM, PANEL_END = "2026-02-02", "2026-10-26"   # look-back window start (>= 148 panel days before the first tape day: scen_lab indexes day 147); last day of the 5-year Dhan panel
M0, NB = 555, 375
SYMS = {"NIFTY": dict(pre="NSE_FNO:NIFTY", idx="NSE_IDX:NIFTY", step=50), "SENSEX": dict(pre="BSE_FNO:SENSEX", idx="BSE_IDX:SENSEX", step=100)}
os.environ.setdefault("FIN1_TAPE", str(TAPE)); os.environ.setdefault("FIN1_DATA", str(ROOT / "data")); sys.path.insert(0, str(HERE))   # read by fin1_shadow at import
IST = ZoneInfo("Asia/Kolkata"); CALM = 1.0042; MED_RVIV = 0.5434115813664702   # fin1_shadow THRESH (4 dp, as sweep_lab OPEN=calm) and its frozen rest-of-day RV/IV median
SEEN_UNTIL = {"E54": "2026-11-16"}                      # last day a cell family had already been looked at, when it is later than PANEL_END (E54: frozen 11-16 on discovery days up to 10-29)
seen_until = lambda cell: SEEN_UNTIL.get(cell.split(".")[0], PANEL_END)
MIN_N, MIN_CAND = 20, 40                                # a bucket below 20 trades is 'too few to judge'; a filter needs 40 to be proposed
MIN_DAYS, CAND_DAYS = 5, 10                             # ... and at least this many different days (2,000 tick trades on one expiry day are one day's weather)

# ---------------------------------------------------------------- the roster, frozen: cell -> (registry row, fill, prior trading days needed, rule as registered)
R_ = lambda reg, fill, hist, rule: (reg, fill, hist, rule)
ROSTER = {
    "SH.LSTRAD": R_("E4 base", "shadow", 0, "baseline: buy ATM CE+PE 09:46, sell 15:15, every day (FIN1 without its gate)"),
    "SH.FIN1": R_("FIN1/E4", "shadow", 0, "long ATM straddle 09:46 -> 15:15 when opening RV/IV > 1.0041598"),
    "SH.S1": R_("E3", "shadow", 0, "short ATM straddle 09:47, exit on a 2-step spot move else 15:15, every day"),
    "SH.S2": R_("E3", "shadow", 0, "S1 when opening RV/IV <= 1.0041598"),
    "SH.SC1": R_("SC1", "shadow", 21, "S1 after a contracting day (prior range < 0.7 x mean of the 20 before)"),
    "SH.B1": R_("B1", "shadow", 21, "Crabel NR4 stretch breakout, long ATM, own caps"),
    "SH.IVS": R_("E39 PASS", "shadow", 0, "expiry day, calm open, first 1-pt ATM IV fall -> short OTM1 strangle, spot 1.5 / 30% credit stop / 15:15"),
    "SH.XS": R_("E42 control", "shadow", 0, "expiry day, short OTM1 strangle at 10:08, same exits, no gate"),
    "SH.E33_SCE": R_("E33", "shadow", 21, "E33 lead cells TREND_UP|BEAR, TREND_UP|NEUT, LEVEL|BEAR -> short ATM CE, super-order exits"),
    "SH.E33_LPE": R_("E33", "shadow", 21, "E33 lead cell LEVEL|BEAR -> long ATM PE, super-order exits"),
    "E54": R_("E54", "tick", 0, "expiry-day event bot: V1..V6 x ATM/OTM1/OTM2/SELF x 3/2/60s, 5/3/120s, 10/5/300s (one ledger cell each)"),
    "E39.S1": R_("E39", "bars", 0, "short ATM straddle 09:47, 2-step spot exit"),
    "E39.S2": R_("E39", "bars", 0, "S1 when or_iv <= 0.9338 (fixed: the LEARN q0.7 of the registered E39 run on lab5y_full; the later w10 re-run fitted 0.9295, same verdict)"),
    "E39.SGATE": R_("E39", "bars", 21, "S2 and prior range < 0.7x, NIFTY only"),
    "E39.B1": R_("E39", "bars", 11, "Crabel NR4 stretch breakout (book_lab.sig_b1), long ATM"),
    "E39.E33LB": R_("E39", "bars", 21, "first 15-min slot in LEVEL|BEAR -> short ATM CE (spot cap 2.5, stop 1.5x, target 50%)"),
    "E39.E33POL": R_("E39", "bars", 1, "regime-only policy, table fixed from the registered E39 run on lab5y_full: short ATM CE in TREND_DN, when flat (the w10 re-run learned another table; both FAIL)"),
    "E39.E36IVDN": R_("E39", "bars", 0, "first 1-pt IV drop over 15 min on a 5m bar -> short OTM1 strangle, E33 exits"),
    "E39.IVS": R_("E39 PASS", "bars", 0, "IVS as SH.IVS, on the lab engine's fills (gates DTE=0, OPEN=calm); IV here is Black-Scholes on tape mids, not Dhan's column"),
    "E39.GAPGO": R_("E39/E31#3", "bars", 21, "gap 0.2% go at 09:45, ATM, target 1 / stop 1 step, GAP=FLAT days"),
    "E31.T2": R_("E31#2", "bars", 21, "CRABEL crabel2_w5_k0.75_nr4, ATM, t1_s1, GAP=FLAT"),
    "E31.T4": R_("E31#4", "bars", 21, "short ATM straddle after a 0.5-pt IV fall, spot 2, PRNG=NR days"),
    "E31.T5": R_("E31#5", "bars", 1, "WILLIAMS williams2_k1.2, OTM1, t2_s1, NIFTY"),
    "BAR.XS": R_("E39s", "bars", 0, "XS as SH.XS, on the lab engine's fills"),
    "BAR.IVX": R_("E42", "bars", 0, "IVS without the calm-open gate (expiry day, first 1-pt IV fall)"),
    "E43.XS_W3": R_("E43", "bars", 0, "XS + long OTM3 wings (iron condor 1/3)"), "E43.XS_W4": R_("E43", "bars", 0, "XS + long OTM4 wings"),
    "E43.IVS_W3": R_("E43", "bars", 0, "IVS + long OTM3 wings"), "E43.IVS_W4": R_("E43", "bars", 0, "IVS + long OTM4 wings"),
    "E41.RATIO": R_("E41", "bars", 0, "expiry day 09:20: long 1 ATM CE+PE, short 3x the one-third-premium strikes, to 15:15"),
    "E51.OIX": R_("E51", "bars", 1, "expiry 14:00 change-in-OI imbalance -> buy the ATM option (needs ATM+-5 OI today and yesterday)"),
    "E51.SC": R_("E51", "bars", 1, "5m super candle call, strike by premium = 1% of spot"),
    "E51.PIV": R_("E51", "bars", 1, "15m ADX + 5m Supertrend + Fibonacci pivot break, ITM1"),
    "E51.F44": R_("E51", "bars", 0, "buy the 44% recovery of a 0.5% intraday fall, ATM CE"),
    "E51.OVW": R_("E51", "bars", 0, "sell the ATM option below its own VWAP with rising OI (needs volume)"),
    "E53.GS": R_("E53", "bars", 1, "gap day: sell the 1.0-1.5% OTM option of the gap side at 09:29"),
    "E53.GSm": R_("E53 control", "bars", 1, "GS mirrored (control row)"),
    "E53.PR": R_("E53", "bars", 0, "premium race: the first side whose option crosses 0.735% of spot 09:25-09:34"),
    "E53.A220": R_("E53", "bars", 0, "14:20 five-minute bar break, long ATM"),
    "E53.PCR": R_("E53", "bars", 1, "11:00 change-in-OI PCR -> buy the 0.27%-premium OTM near its VWAP (needs OI yesterday, volume)"),
    "E53.OIC": R_("E53", "bars", 0, "09:29 OI walls ATM+-1..5 -> credit spread at the wall"),
    "E53.ORS": R_("E53", "bars", 0, "opening-range break -> sell the opposite ATM option"),
    "E53.BBH": R_("E53", "bars", 1, "first-hour Bollinger + Heikin Ashi turn on the ATM option's 1m chart (needs volume)"),
}
for _s in ("IFLY1", "ICON12"):
    for _e in ("0946", "1130"):
        for _x in ("spot1", "spot1.5"): ROSTER[f"E37.{_s}.{_e}.{_x}"] = R_("E37", "bars", 0, f"{_s} at {_e}, exit {_x} / stop 1.5x / target 50% (the calm and IV-rank gates are read off the situation table)")
UNTESTABLE = {  # registered cells that cannot be scored on the tape at all, with the reason (printed by `roster`, never silently dropped)
    "E51.GB": "its OI rule ranks a strike in the top 3 of the whole ATM+-10 chain; the tape holds about ATM+-4/5",
    "E48 hero-zero (64 cells)": "cheap OTM strikes sit a median 6.6 steps out; tape reach is about ATM+-4/5 (E54's V5 covers cheap bursts on the tick tape from 11-17, when the expiry ladder widened to +-8)",
    "E40 pre-RBI": "opt1y_lab.RBI has no MPC date after 2026-10-07: no event can fire until the Dec-2026 date is registered",
    "E15 GIFT / E16-E17 chain / E22 participant OI / E12 / E19 / E20": "need data that is not on the tape (outside files, the other index's overnight leg, T-1 bhavcopy)",
}
LEFT_OUT = {  # registered and testable in principle, but not wired in (said, not hidden)
    "E31 other 247k variants, E36 atlas (40 patterns), E42 atlas (145 cells)": "mass sweeps whose survivors are already cells here (E31 top-5, E36 IV-drop, E42 = IVS re-count); the rest are PARKED nulls by family",
    "E44 / E45 1m scalps (42 cells)": "scalp_lab pools its own arrays from panel.pkl over all days at once; no per-day entry point (0 of 42 passed)",
    "E46 / E49 tick scalps, E52 ML ceiling": "need the frozen discovery / holdout day lists or a fitted model; E54 is the live tick-tape descendant and is scored",
    "E1-E14, E18, E21, E23-E30, B2-B10": "rejected on the 1-year panel before the 5-year re-test; the E39 list is the set the registry carried forward",
    "E37 with the IV-rank-high gate (8 cells)": "the bench has no IV-rank tag; E37 runs ungated and its calm-open gate is read off the oriv situation",
    "E47 rich-credit skip": "a filter on IVS / XS, not a trade: fin1_shadow already logs rel_cred / rich per trade",
}
BASE = {"SH.FIN1": "SH.LSTRAD", "SH.S2": "SH.S1", "SH.SC1": "SH.S1", "SH.IVS": "SH.XS", "E39.S2": "E39.S1", "E39.SGATE": "E39.S1", "E39.IVS": "BAR.XS",
        "BAR.IVX": "BAR.XS", "E43.IVS_W3": "E43.XS_W3", "E43.IVS_W4": "E43.XS_W4"}       # random-day placebo: the same structure without the gate
PAIRS = [("SH.S1", "E39.S1"), ("SH.IVS", "E39.IVS"), ("SH.XS", "BAR.XS"), ("SH.B1", "E39.B1")]  # same rule, real quotes vs the engine's bar fills


# ---------------------------------------------------------------- calendar
def holidays():
    return {m for f in (HERE.parents[1] / "config/v2/calendar").glob("nse_holidays_*.yaml") for m in re.findall(r"date:\s*(\d{4}-\d\d-\d\d)", f.read_text())}


def tdays_before(day, n, hol=None):
    """the n trading days before `day`, newest first (weekdays minus the listed NSE holidays; ponytail: an unlisted year counts every weekday,
    so a missing holiday file reads as a history hole = cells go UNTESTABLE, never the other way)."""
    hol = holidays() if hol is None else hol; out = []; d = date.fromisoformat(day)
    while len(out) < n:
        d -= timedelta(1)
        if d.weekday() < 5 and d.isoformat() not in hol: out.append(d.isoformat())
    return out


hm = lambda i: f"{(M0 + i) // 60:02d}:{(M0 + i) % 60:02d}"   # bar index from 09:15 -> HH:MM


# ---------------------------------------------------------------- converter: tick tape -> the 5-year panel's 1-minute rows (opt1y_load format)
def _iv(p, S, K, T, cp):
    from fin1_shadow import implied_vol   # the shadow's Black-Scholes (r 6.5%), reused
    return implied_vol(p, S, K, T, cp) if p > 0 and S > 0 else float("nan")


def to_bars(T, day, vol=None):
    """T: ticks (t = receipt ms since midnight IST, iid, bid, ask, ltp, oi), as tapelib.study_tapecache writes them. -> (rows, cov).
    rows = opt1y format: one row per (sym, side, strike, minute m) of the nearest expiry: o/h/l/c of the quote MID inside minute m (stamped at
    the minute start, as Dhan's bars), oi = last print, spot = the index's last ltp of the minute (carried forward), off = strike steps
    from round(spot / step), iv = Black-Scholes on the close MID with the calendar minutes left to 15:30 of the expiry day (NOT Dhan's IV column:
    `check` shows a median absolute gap of 0.25-0.8 pt at ATM+-2, so a 1-pt IV-fall trigger can fire at a different minute than on Dhan bars), vol from `vol` {(iid, m): traded qty} else NaN. Minutes before the first index tick
    are dropped (no spot = no ATM). cov[sym]: first / last index minute, expiry, strike reach, full = the whole session is on tape."""
    T = T.assign(iid=T.iid.astype(str), m=(T.t // 60000).astype(int)); T = T[(T.m >= M0) & (T.m < M0 + NB)]; out = []; cov = {}
    ts0 = int(datetime.fromisoformat(day).replace(tzinfo=IST).timestamp())
    for sym, c in SYMS.items():
        ix = T[T.iid == c["idx"]].groupby("m").ltp.last(); o = T[T.iid.str.startswith(c["pre"] + ":") & (T.iid.str.count(":") == 4)]
        if not len(ix) or not len(o): cov[sym] = dict(full=False, first=None, last=None, why="no index or no options on tape"); continue
        pr = o.iid.str.split(":", expand=True); exps = [e for e in pr[2].unique() if e >= day]
        if not exps: cov[sym] = dict(full=False, first=None, last=None, why="no live expiry"); continue
        exp = min(exps); o = o.assign(K=pr[3].astype(float), side=pr[4])[(pr[2] == exp) & (o.bid > 0) & (o.ask >= o.bid)]; o = o.assign(mid=(o.bid + o.ask) / 2)
        b = o.groupby(["side", "K", "m"]).agg(iid=("iid", "first"), o=("mid", "first"), h=("mid", "max"), l=("mid", "min"), c=("mid", "last"), oi=("oi", "last")).reset_index()
        spot = ix.reindex(range(M0, M0 + NB)).ffill(); b["spot"] = b.m.map(spot); b = b[b.spot.notna()]
        st = c["step"]; b["off"] = ((b.K - (b.spot / st).round() * st) / st).round().astype(int); dd = (date.fromisoformat(exp) - date.fromisoformat(day)).days
        b["iv"] = [_iv(p, s, k, max(dd * 1440 + 930 - m - 1, 1) / 525600, sd) for p, s, k, m, sd in zip(b.c, b.spot, b.K, b.m, b.side)]
        b["vol"] = [(vol or {}).get((i, m), np.nan) for i, m in zip(b.iid, b.m)]
        b = b.assign(sym=sym, day=day, exp=exp, ts=ts0 + b.m * 60, strike=b.K); out.append(b[["ts", "o", "h", "l", "c", "vol", "oi", "iv", "spot", "strike", "sym", "side", "off", "day", "m", "exp"]])
        r = b.groupby("m").off.agg(["min", "max"]); s = spot.dropna()
        cov[sym] = dict(first=hm(int(ix.index.min()) - M0), last=hm(int(ix.index.max()) - M0), exp=exp, idx_min=int(len(ix)), opt_min=int(b.m.nunique()),
                        reach=[int(r["min"].median()), int(r["max"].median())] if len(r) else None,
                        full=bool(ix.index.min() <= M0 + 1 and ix.index.max() >= M0 + NB - 6 and b.m.nunique() >= 300),
                        bar=[float(s.iloc[0]), float(s.max()), float(s.min()), float(s.iloc[-1])])
    rows = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["ts", "o", "h", "l", "c", "vol", "oi", "iv", "spot", "strike", "sym", "side", "off", "day", "m", "exp"])
    return rows, cov


def snap_vol(day):
    """{(instrument id, minute): quantity traded in the minute} from quote_snapshots' cumulative day volume (about ATM+-4 strikes, from
    2026-10-14 on; older tapes carry none). A minute whose previous minute has no snapshot is left out (NaN), except the 09:15 bar."""
    last = {}; fp = TAPE / day / "quote_snapshots.jsonl"
    if not fp.is_file(): return {}
    with open(fp, encoding="utf-8") as f:
        for ln in f:
            if '"volume":null' in ln or '"volume"' not in ln: continue
            try: e = json.loads(ln); p = e["payload"]; t = e["timestamp"]
            except (ValueError, KeyError): continue
            last[(p["instrument_id"], int(t[11:13]) * 60 + int(t[14:16]))] = p["volume"]
    return {(i, m): v - last[(i, m - 1)] if (i, m - 1) in last else v for (i, m), v in last.items() if (i, m - 1) in last or m == M0}


def is_live(day):
    now = datetime.now(IST); return day == now.date().isoformat() and now.hour * 60 + now.minute < 931


def tick_file(day):
    """the day's tick cache: the shared one if it exists, else built into this bench's own cache dir (never into the shared one, and a
    live day is built into a temp dir so no stale partial cache is left behind for the close jobs)."""
    for d in (TICK, CACHE / "tapetick"):
        if (d / f"{day}.parquet").exists() and not is_live(day): return d / f"{day}.parquet"
    os.environ["TAPE"] = str(TAPE); import tapelib
    if day in _LIVE: return _LIVE[day]
    d = CACHE / "tapetick"
    if is_live(day): d = Path(tempfile.mkdtemp(prefix="fwd_live_")); _LIVE[day] = d / f"{day}.parquet"; atexit.register(shutil.rmtree, d, True)   # removed when this process ends
    tapelib.TAPE, tapelib.TAPEC = str(TAPE), str(d); tapelib.study_tapecache([day]); return d / f"{day}.parquet"


_LIVE = {}


def bars(day):
    """(rows, cov) of a taped day, cached under CACHE/bars (not cached while the day is still being written)."""
    fp, fc = CACHE / "bars" / f"{day}.parquet", CACHE / "bars" / f"{day}.json"
    if fp.exists() and fc.exists(): return pd.read_parquet(fp), json.loads(fc.read_text())
    rows, cov = to_bars(pd.read_parquet(tick_file(day), columns=["t", "iid", "bid", "ask", "ltp", "oi"]), day, snap_vol(day))
    if not is_live(day) and (TAPE / day / "quote_snapshots.jsonl").is_file():   # without the snapshot file the bars carry no volume: usable now, rebuilt (not cached) next time
        fp.parent.mkdir(parents=True, exist_ok=True); rows.to_parquet(fp); fc.write_text(json.dumps(cov))
    return rows, cov


def taped_days():
    return sorted(p.name for p in TAPE.iterdir() if (p / "depth_quotes.jsonl").is_file() and (p / "quote_snapshots.jsonl").is_file() and (p / "depth_quotes.jsonl").stat().st_size > 5e7)


# ---------------------------------------------------------------- situation tags (frozen 2026-11-17, before any bench row existed)
def tod(t): return "09:15-09:45" if t < "09:46" else "09:46-11:00" if t < "11:00" else "11:00-13:00" if t < "13:00" else "13:00-15:30"


def tags(day, exp, bar, prev, ratio):
    """known at the entry: dte (calendar fact), gap (09:15 vs yesterday's close, +-0.25%), prev (yesterday open -> close, +-0.30%),
    oriv (09:45 opening RV / ATM IV <= 1.0042 = CALM; used only for entries from 09:46). bar / prev = [open, high, low, close] or None."""
    d = None if not exp else int(np.busday_count(day, exp, holidays=sorted(holidays()))); g = bar[0] / prev[3] - 1 if bar and prev else None; p = prev[3] / prev[0] - 1 if prev else None
    return dict(dte="NA" if d is None else "D0" if d == 0 else "D1" if d == 1 else "D2+", gap="NA" if g is None else "GAP_UP" if g > 0.0025 else "GAP_DN" if g < -0.0025 else "GAP_FLAT",
                prev="NA" if p is None else "PREV_UP" if p > 0.003 else "PREV_DN" if p < -0.003 else "PREV_FLAT", oriv="NA" if ratio is None or ratio != ratio else "CALM" if ratio <= CALM else "ACTIVE")


def describe(bar, closes=None, iv=None):
    """AFTER THE FACT (never a filter): day type = TREND when |close - open| >= half the day's range else RANGE; rviv = realised vol of the
    1m closes 09:46-15:15 over the 09:45 ATM IV against the frozen median 0.543 (MORE = the day moved more than usual for its IV)."""
    out = dict(daytype="NA", rviv="NA")
    if bar and bar[1] > bar[2]: out["daytype"] = "TREND" if abs(bar[3] - bar[0]) >= 0.5 * (bar[1] - bar[2]) else "RANGE"
    if closes is not None and iv and len(closes) > 60:
        r = np.diff(np.log(np.asarray(closes, float))); out["rviv"] = "MORE" if math.sqrt((r ** 2).sum() * 252 * 375 / len(r)) * 100 / iv > MED_RVIV else "LESS"
    return out


# ---------------------------------------------------------------- ledger: append-only, one row per (day, sym, cell)
def read_ledger(path=None):
    path = Path(path or LEDGER); return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.is_file() else []


def append(rows, path=None):
    """append the rows whose (day, sym, cell) is not in the ledger yet; an ENGINE_ERROR row is never stored (a re-run may fill it). -> n written."""
    path = Path(path or LEDGER); have = {(r["day"], r["sym"], r["cell"]) for r in read_ledger(path)}; new = []
    for r in rows:
        k = (r["day"], r["sym"], r["cell"])
        if k not in have and not str(r.get("status", "")).startswith("ENGINE_ERROR"): have.add(k); new.append(r)
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f: f.write("".join(json.dumps(r) + "\n" for r in new))
    return len(new)


def mk(day, sym, cell, trades=None, status=None, **kw):
    """one ledger row. trades = [dict(t='HH:MM' entry, pnl=Rs net, forced, plc=mean Rs of the engine's placebo twins or None)]."""
    tr = [dict(t=x["t"], pnl=round(float(x["pnl"]), 2), **({"forced": True} if x.get("forced") else {}),
               **({"plc": round(float(x["plc"]), 2)} if x.get("plc") is not None and x["plc"] == x["plc"] else {})) for x in (trades or [])]
    fill = ROSTER.get(cell, ROSTER["E54"] if cell.startswith("E54") else ("", "", 0, ""))[1]
    return dict(day=day, sym=sym, cell=cell, status="TRADE" if tr else (status or "NO_SIGNAL"), n=len(tr), wins=sum(x["pnl"] > 0 for x in tr),
                pnl=round(sum(x["pnl"] for x in tr), 2), trades=tr, fill=fill, seen=day <= seen_until(cell), **kw)


# ---------------------------------------------------------------- engine 1: the shadow book (fin1_shadow, real quotes)
def shadow_cells(day, r):
    """fin1_shadow's row for one sym-day -> bench rows (pure mapping; every non-trade keeps the shadow's own reason)."""
    sym = r["sym"]; ok = r.get("status") == "OK"; st = r.get("status", "NO_DATA"); out = []; T = lambda t, p: [dict(t=str(t)[:5], pnl=p)]
    add = lambda cell, trades=None, status=None: out.append(mk(day, sym, cell, trades, status))
    add("SH.LSTRAD", T("09:46", r["straddle_pnl_inr"]) if ok else None, st)
    add("SH.FIN1", T("09:46", r["pnl_inr"]) if ok and r["signal"] else None, "NO_SIGNAL" if ok else st)
    s1 = r.get("s1_pnl_inr")
    add("SH.S1", T("09:47", s1) if s1 is not None else None, r.get("s1_exit") or r.get("lead_hist") or "NO_INPUT")
    add("SH.S2", T("09:47", r["s2_pnl_inr"]) if ok and r["s2_signal"] and r.get("s2_short_pnl_inr") is not None else None, ("NO_SIGNAL" if not r.get("s2_signal") else "NO_QUOTES") if ok else st)
    hist = r.get("lead_hist") == "OK"
    add("SH.SC1", T("09:47", s1) if hist and r.get("sc1_signal") and s1 is not None else None, "NO_SIGNAL" if hist else "UNTESTABLE:" + str(r.get("lead_hist", "NO_HIST")))
    add("SH.B1", T(r.get("b1_entry_t", "09:20"), r.get("b1_pnl_inr")) if r.get("b1_status") == "TRADE" else None,
        "UNTESTABLE:NO_HIST" if r.get("b1_status") in (None, "NO_HIST") else "NO_SIGNAL" if r["b1_status"] in ("NR4_NO", "NO_CROSS") else r["b1_status"])
    for pre, cell, t0 in (("ivs", "SH.IVS", None), ("xs", "SH.XS", "10:08")):
        s_ = r.get(f"{pre}_status")
        add(cell, T(t0 or r.get("ivs_entry_t", "10:00"), r[f"{pre}_pnl_inr"]) if s_ == "TRADE" else None, st if not ok else "NOT_EXPIRY" if s_ == "GATE_OFF" and r["legs"]["CE"]["expiry"] != day else s_ or "NO_SIGNAL")
    for lead, cell in (("S_CE", "SH.E33_SCE"), ("L_PE", "SH.E33_LPE")):
        tr = [x for x in r.get("e33_trades", []) if x["lead"] == lead]   # without prior days the E33 state has no bias vote and no PDH / PDL level: not the registered rule
        add(cell, [dict(t=x["t_entry"][:5], pnl=x["pnl"], forced="forced" in x.get("why", "")) for x in tr if "pnl" in x] if hist else None,
            "UNTESTABLE:" + str(r.get("lead_hist", "NO_HIST")) if not hist else r.get("e33_status") or ("NO_QUOTES" if tr else "NO_SIGNAL"))
    return out


def run_shadow(day, bar_log):
    """fin1_shadow.day_rows on the tape, unchanged; the per-day index minutes are cached so each 1-2 GB depth file is scanned once."""
    import fin1_shadow as F
    raw = F._tape_spot
    def spot(d):
        fp = CACHE / "spot" / f"{d}.json"
        if fp.exists(): return json.loads(fp.read_text())
        s = raw(d)
        if not is_live(d): fp.parent.mkdir(parents=True, exist_ok=True); fp.write_text(json.dumps(s))
        return s
    F._tape_spot = spot; hist = {}
    for s in F.LOT:
        try: hist[s] = F.prior_days(s, day, log=bar_log)
        except Exception as e: hist[s] = e
    return F.day_rows(day, *F.load(day), hist=hist, prev=F._prev_tape_spot(day)), spot(day)


# ---------------------------------------------------------------- engine 2: the expiry-day tick bot (expiry_bot, E54)
def run_e54(day, cov):
    exp = [s for s in SYMS if (cov.get(s) or {}).get("exp") == day]; out = [mk(day, s, "E54", status="NOT_EXPIRY") for s in SYMS if s not in exp and cov.get(s, {}).get("first")]
    if not exp: return out
    tf = tick_file(day); os.environ.update(TAPE=str(TAPE), TAPEC=str(tf.parent), EBOT_OUT=str(CACHE / "ebot")); import expiry_bot as EB
    for sym, r in EB.replay_day(day, syms=exp).items():
        P = r["prices"]; q = EB.SYM[sym]["q"]
        if not len(P): out.append(mk(day, sym, "E54", status="NO_SIGNAL")); continue
        for (ev, dep, cell), g in P.groupby(["event", "depth", "cell"]):
            f = g[g.filled]
            out.append(mk(day, sym, f"E54.{ev}.{dep}.{cell}", [dict(t=EB._hms(int(s))[:5], pnl=n * q, plc=p * q) for s, n, p in zip(f.slot, f.net, f.plc_net)], "NO_FILL"))
    return out


# ---------------------------------------------------------------- engine 3: the 5-year lab engines on a panel = Dhan history + this day from the tape
def build_panel(day, rows, syms):
    """CACHE/run/<day>/w: opt1y.parquet = the Dhan panel from HIST_FROM to the day before `day` (never later) + full tape days after the
    panel's end + this day's tape rows for `syms`; spreads.csv and ../idx1m.pkl are links to the frozen files. opt1y_lab.build() makes the
    panel from it at import, with its own hygiene, exactly as for the 5-year panel."""
    run = CACHE / "run" / day; shutil.rmtree(run, ignore_errors=True); out = run / "w"; out.mkdir(parents=True)
    assert pd.read_pickle(ROOT / "data/cache/idx1m.pkl").day.max() < day, "idx1m.pkl holds the scored day or later: the engines would read index minutes from the future"
    H = pd.read_parquet(HIST / "opt1y.parquet", filters=[("day", ">=", HIST_FROM), ("day", "<", day)]); parts = [H]
    for d in taped_days():
        if PANEL_END < d < day:
            r, c = bars(d); parts.append(r[r.sym.isin([s for s in SYMS if c.get(s, {}).get("full")])])
    parts.append(rows[rows.sym.isin(syms)]); X = pd.concat(parts, ignore_index=True); X["m"] = X.m.astype("int16")
    X.sort_values(["sym", "side", "off", "ts"]).reset_index(drop=True).to_parquet(out / "opt1y.parquet")
    os.symlink(HIST / "spreads.csv", out / "spreads.csv"); os.symlink(ROOT / "data/cache/idx1m.pkl", run / "idx1m.pkl"); return out


def run_labs(day, rows, syms):
    """-> bench rows of every 'bars' cell for the full sym-days (one subprocess: the lab modules read their panel dir from argv at import)."""
    out = build_panel(day, rows, syms); res = out / "labs.json"
    p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "_labs", day, str(out)], cwd=str(HERE), capture_output=True, text=True)
    if not res.exists():
        err = (p.stderr or p.stdout).strip().splitlines()[-1:] or ["no output"]; print("labs FAILED:", err[0][:300])
        sys.stderr.write(p.stderr[-4000:]); raise RuntimeError("labs subprocess wrote no result: " + err[0][:200])
    R = json.loads(res.read_text())
    if not os.environ.get("FWD_KEEP"): shutil.rmtree(CACHE / "run" / day, ignore_errors=True)
    return [mk(day, x["sym"], x["cell"], [dict(t=hm(t["i"] + 1), pnl=t["pnl"], forced=t["forced"], plc=t.get("plc")) for t in x["trades"]], x["status"]) for x in R]


def _labs(day, out):
    """runs INSIDE the subprocess. Every cell is the engine's own function with the registered parameters; nothing is fitted here."""
    sys.argv = [sys.argv[0], out]; os.environ.update(LAB_FULL="1", HO=day, COSTS="today", EXT=str(ROOT / "data/cache/ext")); sys.path.insert(0, str(HERE))
    import opt1y_lab as L, sell_lab as S
    P = L.P; ks = [k for k in L.ALLK if k[1] == day]; res = {}; nan = float("nan"); fin = np.isfinite
    have = {s: {k[1] for k in L.ALLK if k[0] == s} for s in SYMS}; hole = {n: {s: [d for d in tdays_before(day, n) if d not in have[s]] for s in SYMS} for n in (1, 11, 21)}

    def put(cell, k, r=None, status=None):
        """r: one engine result dict, a list of them, or None. Each carries i (decision bar), pnl, forced, optional pl (placebo twins)."""
        tr = [x for x in (r if isinstance(r, list) else [r] if r else []) if x and fin(x["pnl"])]
        res[(cell, k[0])] = dict(cell=cell, sym=k[0], status=status or ("NO_FILL" if r is not None and not tr else "NO_SIGNAL"),
                                 trades=[dict(i=int(x["i"]), pnl=float(x["pnl"]), forced=bool(x.get("forced")),
                                              plc=float(np.nanmean(x["pl"])) if x.get("pl") is not None and fin(x["pl"]).any() else None) for x in tr])

    def ok(cell, k):
        n = ROSTER[cell][2]
        if n and hole[n][k[0]]: put(cell, k, status="UNTESTABLE:no_prev_day" if hole[1][k[0]] else f"UNTESTABLE:hist_hole_{n}d"); return False
        return True

    def group(cells, fn):
        try: fn()
        except Exception as e:
            import traceback; traceback.print_exc()
            for c in cells:
                for k in ks: res.setdefault((c, k[0]), dict(cell=c, sym=k[0], status=f"ENGINE_ERROR:{type(e).__name__}", trades=[]))

    cl = lambda k, sd, off, i, col=3: L._get(k, sd, P[k]["atm"][i] + off * L.STEP[k[0]], i, col)   # a taped value at a strike offset, NaN if not on tape
    import book_lab as B, sweep_lab as W, playbook_lab as PL, wings_lab as WG, yt_lab as Y
    V = L.vol_days().set_index(["sym", "day"])

    def g_e39():
        Dp = B.prep()
        for k in ks:
            r = S.struct(k, 31, S.SSTRAD, sstop=2, mode="cons"); orv = V.or_iv.get(k, nan); put("E39.S1", k, r, None if r else "NO_FILL")
            calm = orv <= 0.9338; put("E39.S2", k, r if calm else None, "NO_SIGNAL" if not calm else None if r else "NO_FILL")
            if ok("E39.SGATE", k):
                g = calm and k[0] == "NIFTY" and k in Dp.index and Dp.rr1.get(k, nan) < 0.7; put("E39.SGATE", k, r if g else None, "NO_SIGNAL" if not g else None if r else "NO_FILL")
            if ok("E39.B1", k):
                sg = B.sig_b1(k, Dp.loc[k]) if k in Dp.index else []
                put("E39.B1", k, [next((r for i, sd, ex in sg for r in [S.struct(k, i, [(sd, 0, 1)], dirn=1 if sd == "CE" else -1, mode="cons", **ex)] if r), None)] if sg else None)   # the first signal that fills, as study_e39
    group(["E39.S1", "E39.S2", "E39.SGATE", "E39.B1"], g_e39)

    def g_e33():
        A = PL.Z.labs()[0]; Dt = PL.daytab(); ivp = V.ivpct.to_dict()
        for k in ks:
            G = PL._bars5(k); F = PL.states(pd.DataFrame([PL._row33(k, i, G, A.loc[k], Dt[k], ivp.get(k, nan)) for i in PL.SLOTS33]))
            if ok("E39.E33LB", k):
                put("E39.E33LB", k, next(([r] for i, c in zip(F.i, F.cell) if c == "LEVEL|BEAR" for r in [PL.act33(k, int(i), "S_CE")] if r), None))
            if ok("E39.E33POL", k):
                busy = -1; tr = []
                for i, reg in zip(F.i, F.regime):   # playbook_lab.run33 with the E39 table {TREND_DN: S_CE}
                    r = PL.act33(k, int(i), "S_CE") if i > busy and reg == "TREND_DN" else None
                    if r: tr.append(dict(r, i=int(i))); busy = i + 1 + r["held"]
                put("E39.E33POL", k, tr or None)
            i = next((x["i"] for x in PL.e36_rows(k) if x["iv_dn"]), None); r = PL.act33(k, i, "S_STRANGLE1") if i is not None else None
            put("E39.E36IVDN", k, [dict(r, i=i)] if r else None, "NO_FILL" if i is not None and not r else None)
            for sn, legs in PL.E37_STR.items():
                for en, i in PL.E37_ENT.items():
                    for xn, ex in PL.E37_EX.items():
                        r = S.struct(k, i, legs, mode="cons", **ex); put(f"E37.{sn}.{en}.{xn}", k, r, None if r else "NO_FILL")
    group(["E39.E33LB", "E39.E33POL", "E39.E36IVDN"] + [c for c in ROSTER if c.startswith("E37.")], g_e33)

    def g_sweep():
        Gm = W.gate_matrix(); gi = {g[0]: n for n, g in enumerate(W.GATES)}
        for cid, cell, gates in (("E39.IVS", ("ND_STRANGLE1", "ivfall1.0", "STRANGLE1", "spot1.5_stop0.3"), ["DTE=0", "OPEN=calm"]),
                                 ("E39.GAPGO", ("GAP", "gap0.2_go_at30", "ATM", "t1_s1"), ["GAP=FLAT"]), ("E31.T2", ("CRABEL", "crabel2_w5_k0.75_nr4", "ATM", "t1_s1"), ["GAP=FLAT"]),
                                 ("E31.T4", ("ND_SHORT_STRAD", "ivfall0.5", "SHORT_STRAD", "spot2"), ["PRNG=NR"]), ("E31.T5", ("WILLIAMS", "williams2_k1.2", "OTM1", "t2_s1"), ["SYM=NIFTY"])):
            r = W.price_cell(cell)
            for k in ks:
                if not ok(cid, k): continue
                if not all(Gm[W.KI[k], gi[g]] for g in gates): put(cid, k, status="GATE_OFF" if P[k]["d0"] or "DTE=0" not in gates else "NOT_EXPIRY"); continue
                m = r[r["k"] == W.KI[k]]; put(cid, k, [dict(i=x["i"], pnl=x["pnl"], forced=x["forced"]) for x in m] or None)
    group(["E39.IVS", "E39.GAPGO", "E31.T2", "E31.T4", "E31.T5"], g_sweep)

    def g_wings():
        E = {nm: dict(v) for nm, v in WG.entries().items()}
        for cid, nm, legs in (("BAR.XS", "XS", WG.STR1), ("BAR.IVX", "IVX", WG.STR1), ("E43.XS_W3", "XS", S.icon(1, 3)), ("E43.XS_W4", "XS", S.icon(1, 4)),
                              ("E43.IVS_W3", "IVS", S.icon(1, 3)), ("E43.IVS_W4", "IVS", S.icon(1, 4))):
            for k in ks:
                if not P[k]["d0"]: put(cid, k, status="NOT_EXPIRY"); continue
                if k not in E[nm]: put(cid, k); continue
                w_ = max(abs(o) for _, o, _ in legs)   # a bought wing (and one step beyond it) must be on tape at the decision bar, else its exit is a bound, not a price
                if w_ > 1 and not all(fin(cl(k, sd, sg * o, E[nm][k])) for sd, sg in (("CE", 1), ("PE", -1)) for o in (w_, w_ + 1)): put(cid, k, status="UNTESTABLE:reach"); continue
                t = WG.price([(k, E[nm][k])], legs).iloc[0]; put(cid, k, [dict(i=t.i, pnl=t.pnl, forced=t.forced)], None if fin(t.pnl) else "NO_FILL")
        for k in ks:   # E41: the one-third-premium strike must be bracketed by a cheaper taped strike, else the pick is the tape's edge, not the rule's strike
            if not P[k]["d0"]: put("E41.RATIO", k, status="NOT_EXPIRY"); continue
            far = lambda sd, sg: min([x for n in range(1, 11) for x in [cl(k, sd, sg * n, 5)] if fin(x)], default=nan)
            if not all(far(sd, sg) <= cl(k, sd, 0, 5) / 3 for sd, sg in (("CE", 1), ("PE", -1))): put("E41.RATIO", k, status="UNTESTABLE:reach"); continue
            r = PL.e41_trade(k); put("E41.RATIO", k, r, None if r else "NO_FILL")
    group(["BAR.XS", "BAR.IVX", "E43.XS_W3", "E43.XS_W4", "E43.IVS_W3", "E43.IVS_W4", "E41.RATIO"], g_wings)

    def g_yt():
        for k in ks:
            sym = k[0]; ksym = Y.keys(sym); d = ksym.index(k); p = P[k]; pp = P[ksym[d - 1]] if d else None; st = L.STEP[sym]; s = p["spot"]
            Y.FE[sym] = Y.feats(ksym); Y.DIX.update({kk: n for n, kk in enumerate(ksym)})
            volok = lambda sd, K, a, b: (lambda x: x is not None and fin(x[a:b, 6]).mean() >= 0.9)(p["C"].get((sd, K)))
            side_px = lambda sd, i: [a[i, 3] for (s_, K), a in p["C"].items() if s_ == sd and fin(a[i, 3])]
            def why(c):   # None = the tape holds everything the rule reads; else the reason it cannot be judged today
                if c == "OIX": return None if not p["d0"] or all(fin(cl(k, sd, o, i, 4)) for sd in ("CE", "PE") for o in range(-5, 6) for i in (165, 285)) else "reach"
                if c == "SC":   # every decision bar needs a traded CE on each side of the 1%-of-spot premium, else the nearest is the tape's edge
                    for i in range(4, 345, 5):
                        v = [a[i, 3] for (s_, K), a in p["C"].items() if s_ == "CE" and fin(a[i, 3]) and a[i, 6] > 0]
                        if not v or not (min(v) <= 0.01 * s[i] <= max(v)): return "reach"
                    return None
                if c == "OVW": return None if all(volok(sd, p["atm"][i], 30, 315) for sd in ("CE", "PE") for i in (34, 174, 314)) else "no_volume"
                if c in ("GS", "GSm"): return None if all(any(sg * (K - s[14]) >= 0.015 * s[14] for (s_, K), a in p["C"].items() if s_ == sd and fin(a[14, 3])) for sd, sg in (("CE", 1), ("PE", -1))) else "reach"
                if c == "PR": return None if all(max(side_px(sd, 9), default=0) > 0.00735 * s[9] for sd in ("CE", "PE")) else "reach"
                if c == "OIC": return None if all(fin(cl(k, "CE", n, 14, 4)) and fin(cl(k, "PE", -n, 14, 4)) for n in range(1, 6)) else "reach"
                if c == "BBH": return None if fin(p["atm"][0]) and all(volok(sd, p["atm"][0], 0, 62) for sd in ("CE", "PE")) else "no_volume"
                if c == "PCR":
                    if p["d0"] or pp is None or str(pp["exp"]) != str(p["exp"]): return None
                    at = p["atm"][:106]; at = at[fin(at)]; N = min(max(int(p["dte"]), 1), 5)
                    if not len(at) or not all(fin(Y.doi(p, pp, sd, at[0] + o * st, 105)) for sd in ("CE", "PE") for o in range(-N, N + 1)): return "reach"
                    v = Y.pcr_val(p, pp, 105, sym); sd = "CE" if v > 1.25 else "PE" if v < 0.75 else None
                    if sd is None: return None
                    if not min(side_px(sd, 105), default=nan) <= 0.0027 * s[105]: return "reach"
                    return None if volok(sd, Y.pcr_strike(p, 105, sym, sd), 105, 285) else "no_volume"
                return None
            sig = {**Y.all_signals(ksym, Y.FE[sym], [d]), **Y.all_signals53(ksym, [d])}
            for c, v in sig.items():
                cid = ("E51." if c in Y.CELLS else "E53.") + c
                if cid not in ROSTER or not ok(cid, k): continue
                w = why(c)
                if w: put(cid, k, status="UNTESTABLE:" + w); continue
                put(cid, k, [(Y._work if c in Y.CELLS else Y._work53)((c, t)) for t in v] if v else None)
    group([c for c in ROSTER if c[:4] in ("E51.", "E53.")], g_yt)
    json.dump(list(res.values()), open(os.path.join(out, "labs.json"), "w"))


# ---------------------------------------------------------------- one day
def _guard(name, fn, fail):
    """one engine block: an exception prints the traceback and a FAILED line and yields fail() (ENGINE_ERROR rows, which are never stored,
    so the next `--again` run fills them). One broken engine never costs the day's other rows."""
    try: return fn()
    except Exception as e:
        traceback.print_exc(); print(f"fwd_bench FAILED {name}: {type(e).__name__}: {str(e)[:200]}", flush=True); return fail()


def score_day(day, dry=False, again=False):
    if not (TAPE / day / "depth_quotes.jsonl").is_file(): print(f"fwd_bench {day}: no tape"); return []
    L = read_ledger(); live = is_live(day)
    if any(r["day"] == day for r in L) and not dry and not again: print(f"fwd_bench {day}: already logged ({sum(r['day'] == day for r in L)} rows); the ledger is append-only (--again re-scores and appends only rows that are missing)"); return []
    B = _guard("converter", lambda: bars(day), lambda: None)
    if B is None: print(f"fwd_bench {day}: nothing logged (the tape could not be converted); the next run retries"); return []
    rows, cov = B; out = []; on = [s for s in SYMS if (cov.get(s) or {}).get("first")]; full = [s for s in on if cov[s].get("full")]
    cells = lambda fill: [c for c, v in ROSTER.items() if v[1] == fill]
    S_ = _guard("shadow", lambda: run_shadow(day, [dict(sym=r["sym"], day=r["day"], bar=r.get("bar6")) for r in L if r["cell"] == "_DAY"]), lambda: None)
    sh, spot = S_ or ([], {}); bysym = {r["sym"]: r for r in sh}; pd_ = tdays_before(day, 1)[0]
    hist = pd.read_parquet(HIST / "opt1y.parquet", filters=[("day", "==", pd_)], columns=["sym", "m", "spot"]) if pd_ <= PANEL_END else None
    for sym in on:
        c = cov[sym]; r = bysym.get(sym, {}); prev = None
        if hist is not None and (hist.sym == sym).any(): g = hist[hist.sym == sym].groupby("m").spot.median(); prev = [float(g.iloc[0]), float(g.max()), float(g.min()), float(g.iloc[-1])] if len(g) >= 300 else None
        else: prev = next((x["bar"] for x in L if x["cell"] == "_DAY" and x["sym"] == sym and x["day"] == pd_ and x.get("status") == "FULL"), None)
        bar = c["bar"] if c.get("full") else None; sp = spot.get(sym, {}); cls = [sp[k] for k in sorted(sp) if "09:46" <= k <= "15:15"]
        opn = c["bar"] if c["first"] <= "09:16" else None   # the gap tag needs only the first minute: it must not depend on the recorder surviving the day
        # the day row carries the shadow's 09:45 ratio: when the shadow failed it is an ENGINE_ERROR row (not stored) so a later run writes it complete
        out.append(dict(day=day, sym=sym, cell="_DAY", status=("FULL" if c.get("full") else "PARTIAL") if S_ else "ENGINE_ERROR:shadow", seen=day <= PANEL_END, cov=c, bar=bar, bar6=r.get("bar"),
                        tags=tags(day, c.get("exp"), opn, prev, r.get("ratio") if r.get("status") == "OK" else None), desc=describe(bar, cls, r.get("iv_atm"))))
        out += shadow_cells(day, r) if r else [mk(day, sym, x, status="ENGINE_ERROR:shadow") for x in cells("shadow")]
    out += _guard("e54", lambda: run_e54(day, cov), lambda: [mk(day, s, "E54", status="ENGINE_ERROR:e54") for s in on])
    out += [mk(day, s, c, status="UNTESTABLE:partial_tape") for s in on if s not in full for c in cells("bars")]
    if full: out += _guard("labs", lambda: run_labs(day, rows, full), lambda: [mk(day, s, c, status="ENGINE_ERROR:labs") for s in full for c in cells("bars")])
    n = 0 if dry or live else append(out); T = [r for r in out if r.get("n")]
    print(f"fwd_bench {day}: {', '.join(f'{s} ' + ('FULL' if s in full else 'PARTIAL from ' + str(cov[s]['first'])) for s in on)}; "
          f"{sum(r['n'] for r in T)} trades in {len(T)} cell-rows, net Rs {sum(r['pnl'] for r in T):,.0f} (summed over all cells: not a book); "
          f"{sum(str(r.get('status', '')).startswith('UNTESTABLE') for r in out)} untestable, {sum(str(r.get('status', '')).startswith('ENGINE_ERROR') for r in out)} engine errors; "
          + ("LIVE tape: NOT logged" if live else "dry run: not logged" if dry else f"{n} rows appended"))
    return out


def backfill():
    done = {r["day"] for r in read_ledger()}
    for d in taped_days():
        if d in done or is_live(d): print(f"{d}: {'logged' if d in done else 'live, skipped'}"); continue
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "day", d], capture_output=True, text=True)
        print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if l.startswith(("fwd_bench", "labs FAILED"))) or f"{d}: no output", flush=True)


# ---------------------------------------------------------------- report
def _p_base(x, base, n=2000, seed=7):
    """random-day placebo: share of n draws of len(x) of the ungated book's trades whose total >= the cell's total (1.0 = no better than chance)."""
    if len(base) < len(x) or not len(x): return None
    rg = np.random.default_rng(seed); b = np.asarray(base, float); return float(np.mean([rg.choice(b, len(x), replace=False).sum() >= sum(x) for _ in range(n)]))


def _p_twin(d, n=4000, seed=7):
    """engine placebo twins (random minute, same day and structure): one-sided bootstrap p that the mean excess (trade - twins) is <= 0."""
    d = np.asarray(d, float); return float((np.random.default_rng(seed).choice(d, (n, len(d))).mean(1) <= 0).mean()) if len(d) > 1 else None


def _p_units(tot, inb, n=10000, seed=7):
    """a bucket made of whole (day, index) units (gap, prev, dte, sym, oriv are day-level): share of random same-COUNT sets of units whose
    total <= the bucket's total. Trades of one day share that day's weather, so the unit, not the trade, is what gets shuffled."""
    tot = np.asarray(tot, float); inb = np.asarray(inb, bool); m = int(inb.sum()); rg = np.random.default_rng(seed)
    if not 0 < m < len(tot): return None
    draw = tot[np.argsort(rg.random((n, len(tot))), axis=1)[:, :m]].sum(1)   # n random sets of m units
    return float((1 + (draw <= tot[inb].sum() + 1e-9).sum()) / (n + 1))      # +1: the observed split counts, so p is never 0


def _p_within(d, n=4000, seed=7):
    """a bucket that splits a unit (time of day): d = per unit (bucket mean - rest mean); sign-flip p, one-sided (the bucket is worse)."""
    d = np.asarray(d, float); return float((1 + ((np.random.default_rng(seed).choice([-1.0, 1.0], (n, len(d))) * d).sum(1) <= d.sum()).sum()) / (n + 1)) if len(d) > 1 else None


def trades_frame(L):
    """one line per trade with its day's tags (oriv only when the entry is from 09:46: before that the tag is not known yet). fwd is
    computed here from the cell's own cutoff (SEEN_UNTIL), never read from the stored flag; partial = the tape did not hold the whole session."""
    D = {(r["day"], r["sym"]): r for r in L if r["cell"] == "_DAY"}; out = []
    for r in L:
        d = D.get((r["day"], r["sym"])) or {}
        for t in r.get("trades") or []:
            tg = d.get("tags", {}); ds = d.get("desc", {})
            out.append(dict(day=r["day"], sym=r["sym"], cell=r["cell"], pnl=t["pnl"], plc=t.get("plc", np.nan), fwd=r["day"] > seen_until(r["cell"]), forced=bool(t.get("forced")),
                            partial=d.get("status") != "FULL", tod=tod(t["t"]), dte=tg.get("dte", "NA"), gap=tg.get("gap", "NA"), prev=tg.get("prev", "NA"),
                            oriv=tg.get("oriv", "NA") if t["t"] >= "09:46" else "PRE_0945", daytype=ds.get("daytype", "NA"), rviv=ds.get("rviv", "NA")))
    return pd.DataFrame(out, columns=["day", "sym", "cell", "pnl", "plc", "fwd", "forced", "partial", "tod", "dte", "gap", "prev", "oriv", "daytype", "rviv"])


DIMS = ["sym", "dte", "gap", "prev", "oriv", "tod"]


def _kept_p(rest, cell, F):
    """does the part of the cell a filter would KEEP beat its placebo? per (day, index) unit: engine twins if the trades carry them, else the
    ungated book (BASE) on forward days; None = the cell has no placebo, so nothing can be proposed from it."""
    u = lambda g, col: g.assign(x=col).groupby(["day", "sym"]).x.sum().values
    if rest.plc.notna().sum() >= MIN_N: k = rest[rest.plc.notna()]; return _p_twin(u(k, k.pnl - k.plc))
    if cell in BASE: return _p_base(u(rest, rest.pnl), u(F[F.cell == BASE[cell]], F[F.cell == BASE[cell]].pnl))
    return None


def learn(T):
    """Works on FORWARD trades only (each cell's own cutoff) and never on forced (bound-priced) ones.
    CANDIDATE = a (cell, bucket) with >= MIN_CAND forward trades on >= CAND_DAYS forward days that (1) loses while the rest of the cell does
    not, (2) is worse than random at p < alpha, where the shuffle is over whole (day, index) units (`_p_units`; inside-the-day buckets:
    `_p_within`), and (3) the kept rest beats its placebo at the same alpha (`_kept_p`). alpha = 0.05 / buckets looked at.
    Everything else is WATCH. Never applied here: a candidate is only a proposal for a future pre-registered E row."""
    F = T[T.fwd & ~T.forced]; F = F.assign(u=F.day + "|" + F.sym); looked = []; watch = []
    for cell, g in F.groupby("cell"):
        for dim in DIMS:
            whole = bool((g.groupby("u")[dim].nunique() == 1).all())
            for b, h in g.groupby(dim):
                if b == "NA" or len(h) == len(g) or len(h) < 5: continue
                rest = g[g[dim] != b]; row = dict(cell=cell, dim=dim, bucket=b, n=len(h), days=h.day.nunique(), mean=h.pnl.mean(), rest_n=len(rest), rest_mean=rest.pnl.mean())
                if len(h) < MIN_CAND or row["days"] < CAND_DAYS: watch.append(row); continue
                if whole: U = g.groupby("u").pnl.sum(); row["p"] = _p_units(U.values, (g.groupby("u")[dim].first() == b).reindex(U.index).values)
                else: row["p"] = _p_within((h.groupby("u").pnl.mean() - rest.groupby("u").pnl.mean()).dropna().values)
                row["kept_p"] = _kept_p(rest, cell, F); looked.append(row)
    a = 0.05 / max(len(looked), 1)
    for r in looked: r["verdict"] = "CANDIDATE" if r["mean"] < 0 and r["rest_mean"] > 0 and r["p"] is not None and r["p"] < a and r["kept_p"] is not None and r["kept_p"] < a else "WATCH"
    return looked, sorted(watch, key=lambda r: r["mean"] - r["rest_mean"])


def report(since=None, short=False, L=None):
    L = read_ledger() if L is None else L; L = [r for r in L if not since or r["day"] >= since]; D = [r for r in L if r["cell"] == "_DAY"]; T = trades_frame(L); out = []; w = out.append
    days = sorted({r["day"] for r in D}); fd = [d for d in days if d > PANEL_END]; full = sum(r["status"] == "FULL" for r in D)
    w(f"Forward bench: {len(days)} taped days{' since ' + since if since else ''} ({days[0]}..{days[-1]}), {len(D)} index-days of which {full} full sessions; "
      f"{len(fd)} days are true forward (after {PANEL_END}), the rest replay days the labs had already seen; "
      f"for the tick bot E54 forward starts after {SEEN_UNTIL['E54']} ({sum(d > SEEN_UNTIL['E54'] for d in days)} day)." if days else "Forward bench: no rows yet")
    if not days: return "\n".join(out)
    un = sum(str(r.get("status", "")).startswith("UNTESTABLE") for r in L); w(f"{len(T)} trades in {T.cell.nunique()} cells; {un} cell-days untestable on the tape (reason logged per row). Rs net at 10 lots, each engine's own fills and charges.")
    S = []
    for cell, g in T.groupby("cell"):
        f = g[g.fwd]; r = dict(cell=cell, days=g.day.nunique(), n=len(g), wins=int((g.pnl > 0).sum()), net=g.pnl.sum(), mean=g.pnl.mean(), fwd_n=len(f), fwd_net=f.pnl.sum(),
                               forced=g.forced.mean() * 100, part=g.partial.mean() * 100, plac="-", p=np.nan, ok=len(g) >= MIN_N and g.day.nunique() >= MIN_DAYS)
        if not r["ok"]: r["plac"] = f"too few (n<{MIN_N} or <{MIN_DAYS} days)"
        elif r["forced"] > 10: r["plac"] = "INCONCLUSIVE: over 10% of exits are bound-priced (forced)"
        elif g.plc.notna().sum() >= MIN_N: x = (g.pnl - g.plc).dropna(); r["p"] = _p_twin(x.values); r["plac"] = f"vs twins {x.mean():+,.0f} p {r['p']:.3f}"
        elif cell in BASE:
            p = _p_base(g.pnl.values, T[T.cell == BASE[cell]].pnl.values); r["p"] = np.nan if p is None else p; r["plac"] = f"vs {BASE[cell]} p {p:.3f}" if p is not None else "base too small"
        else: r["plac"] = "no placebo for this cell"
        S.append(r)
    cols = ["cell", "days", "n", "wins", "net", "mean", "fwd_n", "fwd_net", "forced", "part", "plac", "p", "ok"]
    S = pd.DataFrame(S).sort_values("net", ascending=False) if S else pd.DataFrame(columns=cols); nt = int(S.p.notna().sum()); alpha = 0.05 / max(nt, 1)
    S["plac"] = [x + (" *" if p == p and p < alpha else "") for x, p in zip(S.plac, S.p)]
    if short:
        J = S[S.ok]
        if not len(J): w(f"Nothing judgeable yet: no cell has {MIN_N} trades on {MIN_DAYS} days.")
        else:
            w(f"{len(J)} cells have {MIN_N}+ trades on {MIN_DAYS}+ days; {int((J.p < alpha).sum())} beat their placebo at the Bonferroni alpha {alpha:.4f} ({nt} cells tested). Largest and smallest net (not a test):")
            for r in pd.concat([J.head(3), J.tail(3)]).drop_duplicates("cell").itertuples(): w(f"  {r.cell}: n {r.n} on {r.days} days, wins {r.wins}, net Rs {r.net:,.0f}, forward-only n {r.fwd_n} net {r.fwd_net:,.0f} [{r.plac}]")
        lk, _ = learn(T); c = [r for r in lk if r["verdict"] == "CANDIDATE"]
        w(f"Learn (forward trades only): {len(c)} filter candidate(s), {len(lk)} buckets with >= {MIN_CAND} trades on >= {CAND_DAYS} days looked at" + "".join(f"; {r['cell']} skip {r['bucket']}" for r in c)); return "\n".join(out)
    w("\n== per cell (all taped days | forward-only days, each cell's own cutoff) ==")
    w(f"placebo p values are unadjusted; {nt} cells are tested, so the Bonferroni alpha is {alpha:.4f} (* marks a p below it). forced% = exits priced by a bound; part% = trades on partial-tape days.")
    w(f"{'cell':26s} {'days':>4s} {'n':>5s} {'wins':>5s} {'net Rs':>11s} {'mean':>9s} | {'fwd n':>5s} {'fwd net':>10s} {'forced%':>7s} {'part%':>5s}  placebo")
    for r in S.itertuples(): w(f"{r.cell:26s} {r.days:4d} {r.n:5d} {r.wins:5d} {r.net:11,.0f} {r.mean:9,.0f} | {r.fwd_n:5d} {r.fwd_net:10,.0f} {r.forced:7.0f} {r.part:5.0f}  {r.plac}")
    idle = sorted(c for c in ROSTER if c != "E54" and c not in set(T.cell)); st = pd.DataFrame([r for r in L if r["cell"] in idle])
    if len(idle): w("\nno trade yet: " + "; ".join(f"{c} ({', '.join(f'{k} x{v}' for k, v in st[st.cell == c].status.value_counts().head(3).items()) if len(st) else 'no rows'})" for c in idle))
    w(f"\n== what works where (tags known at the entry; a cell needs {MIN_N} trades on {MIN_DAYS} days in a bucket to be judged) ==")
    for dim in DIMS:
        for b, g in T.groupby(dim):
            if b == "NA": continue
            w(f"{dim}={b}: {len(g)} trades on {g.day.nunique()} days")
            for nm, h in (("tick bot E54", g[g.cell.str.startswith("E54")]), ("other cells ", g[~g.cell.str.startswith("E54")])):
                if not len(h): continue
                c = h.groupby("cell").agg(n=("pnl", "size"), net=("pnl", "sum"), days=("day", "nunique")); big = c[(c.n >= MIN_N) & (c.days >= MIN_DAYS)].sort_values("net")
                f_ = lambda i, r: f"{i} n {int(r.n)} / {int(r.days)} d net {r.net:,.0f}"
                if len(big): w(f"    {nm}: judgeable {len(big)} cells; smallest net " + "; ".join(f_(i, r) for i, r in big.head(2).iterrows()) + " | largest net (not tested) " + "; ".join(f_(i, r) for i, r in big.tail(2).iloc[::-1].iterrows()))
                else: w(f"    {nm}: too few to judge (no cell with {MIN_N} trades on {MIN_DAYS} days); largest net so far {f_(c.net.idxmax(), c.loc[c.net.idxmax()])}, smallest {f_(c.net.idxmin(), c.loc[c.net.idxmin()])} (not tested)")
    w("\n== descriptive only (labels known AFTER the close; never a filter) ==")
    for dim in ("daytype", "rviv"):
        for b, g in T.groupby(dim):
            if b != "NA": w(f"{dim}={b}: {len(g)} trades, {g.day.nunique()} days, long-premium cells net {g[g.cell.isin(['SH.LSTRAD', 'SH.FIN1'])].pnl.sum():,.0f}, short-premium cells net {g[g.cell.isin(['SH.S1', 'E39.S1', 'SH.XS', 'BAR.XS'])].pnl.sum():,.0f}")
    w("\n== fills: the same rule on real quotes (SH) vs the lab engine's bar fills, same index-days ==")
    for a, b in PAIRS:
        x = T[T.cell == a].groupby(["day", "sym"]).pnl.sum(); y = T[T.cell == b].groupby(["day", "sym"]).pnl.sum(); j = pd.concat([x, y], axis=1, keys=["sh", "bar"]).dropna()
        w(f"{a} vs {b}: " + (f"{len(j)} common trades, shadow mean {j.sh.mean():,.0f}, engine mean {j.bar.mean():,.0f}, engine minus shadow {(j.bar - j.sh).mean():+,.0f} per trade" if len(j) else "no common trade yet"))
    lk, wa = learn(T); w(f"\n== learn (FORWARD trades only, forced exits left out; never applied here: a CANDIDATE is only a proposal for a future pre-registered E row) ==")
    w(f"buckets with >= {MIN_CAND} forward trades on >= {CAND_DAYS} forward days looked at: {len(lk)} (Bonferroni alpha {0.05 / max(len(lk), 1):.4f}; shuffles are over whole day-index units); candidates: {sum(r['verdict'] == 'CANDIDATE' for r in lk)}")
    for r in sorted(lk, key=lambda r: (r["verdict"] != "CANDIDATE", r["p"] if r["p"] is not None else 1))[:8]:
        w(f"  {r['verdict']}: {r['cell']} in {r['dim']}={r['bucket']}: n {r['n']} on {r['days']} d mean {r['mean']:,.0f} vs rest n {r['rest_n']} mean {r['rest_mean']:,.0f}, unit-shuffle p {r['p']:.4f}, kept part vs placebo p {'none' if r['kept_p'] is None else format(r['kept_p'], '.4f')}")
    w(f"WATCH (under {MIN_CAND} forward trades or {CAND_DAYS} forward days, cannot be proposed yet; the widest gaps, bucket vs the rest of the same cell):")
    for r in wa[:8]: w(f"  {r['cell']} in {r['dim']}={r['bucket']}: n {r['n']} on {r['days']} d, mean {r['mean']:,.0f} vs rest n {r['rest_n']} mean {r['rest_mean']:,.0f}")
    if not wa: w("  none yet")
    return "\n".join(out)


def roster():
    out = ["RUN (cell | registry row | fill model | prior days needed | rule as registered):"]
    out += [f"  {c:22s} | {v[0]:11s} | {v[1]:6s} | {v[2]:2d} | {v[3]}" for c, v in ROSTER.items()]
    out += ["UNTESTABLE on the tape (whole cell):"] + [f"  {c}: {v}" for c, v in UNTESTABLE.items()]
    out += ["LEFT OUT (not wired in):"] + [f"  {c}: {v}" for c, v in LEFT_OUT.items()]
    out += ["Frozen numbers: S2 0.9338 and the E33 table {TREND_DN: S_CE} are the registered E39 fit on lab5y_full (the w10 confirmation re-run fitted 0.9295 and another table; verdicts equal). "
            "IV on tape bars is Black-Scholes on quote mids (median gap to Dhan's IV 0.25-0.8 pt), so 1-pt IV-fall triggers can fire at another minute than on Dhan bars. "
            f"Forward = after {PANEL_END} for every cell except E54 (after {SEEN_UNTIL['E54']}: it was frozen on discovery days up to 10-29)."]
    out += ["Per day a RUN cell can still log UNTESTABLE:reach / no_volume / no_prev_day / hist_hole_Nd / partial_tape when that day's tape lacks what the rule reads."]
    return "\n".join(out)


def check(day):
    """converter known answer on a day that is BOTH on tape and in the Dhan 5-year panel: same strikes, same minutes."""
    X = pd.read_parquet(HIST / "opt1y.parquet", filters=[("day", "==", day)]); R, cov = bars(day); assert len(X), f"{day} is not in the Dhan panel"
    for sym in SYMS:
        r = R[R.sym == sym]
        if not len(r): print(f"{day} {sym}: not on tape"); continue
        m = X[(X.sym == sym) & (X.vol > 0)].merge(r, on=["side", "strike", "m"], suffixes=("_d", "_t")); a = m[m.off_d.abs() <= 2]
        st = dict(n=len(m), exp=bool((m.exp_d == m.exp_t).all()), close=float(((m.c_t - m.c_d).abs() / m.c_d).median()), spot=float((m.spot_t - m.spot_d).abs().median()),
                  off=float((m.off_d == m.off_t).mean()), oi=float(((m.oi_t - m.oi_d).abs() / m.oi_d.clip(lower=1)).median()), iv=float((a.iv_t - a.iv_d).abs().median()),
                  vol=float((m.vol_t / m.vol_d).median()) if m.vol_t.notna().any() else None)
        print(f"{day} {sym}: {st['n']} common bars; expiry equal {st['exp']}; close gap median {st['close'] * 100:.3f}%; spot gap median {st['spot']:.2f} pts; same ATM offset {st['off'] * 100:.1f}%; "
              f"OI gap median {st['oi'] * 100:.2f}%; IV gap median {st['iv']:.2f} pts (ATM+-2); volume ratio median {st['vol']}")
        assert st["exp"] and st["close"] < 0.005 and st["spot"] < 0.0005 * m.spot_d.median() and st["off"] > 0.9 and st["oi"] < 0.01 and st["iv"] < 1.5, st
    print("check OK: the tape converter reproduces the Dhan panel on", day)


# ---------------------------------------------------------------- selftest: hand-worked known answers, no data, no network
def selftest():
    from fin1_shadow import bs
    day = "2026-11-12"; exp = "2026-11-17"; t = lambda h, m, s=0: (h * 3600 + m * 60 + s) * 1000; iid = lambda K, sd: f"NSE_FNO:NIFTY:{exp}:{K}:{sd}"
    tk = [(t(9, 16, 5), "NSE_IDX:NIFTY", None, None, 25010.0, None), (t(9, 16, 50), "NSE_IDX:NIFTY", None, None, 25030.0, None), (t(9, 18, 10), "NSE_IDX:NIFTY", None, None, 25080.0, None),
          (t(9, 15, 30), iid(25000, "CE"), 99.0, 101.0, 100.0, 500.0),                                        # before the first index tick: dropped
          (t(9, 16, 1), iid(25000, "CE"), 100.0, 102.0, 101.0, 510.0), (t(9, 16, 20), iid(25000, "CE"), 104.0, 106.0, 105.0, 520.0), (t(9, 16, 59), iid(25000, "CE"), 102.0, 103.0, 102.0, 530.0),
          (t(9, 17, 30), iid(25000, "CE"), 0.0, 103.0, 102.0, 531.0),                                         # one-sided quote: no bar
          (t(9, 18, 30), iid(25100, "PE"), 80.0, 81.0, 80.5, 900.0), (t(9, 18, 40), iid(25100, "PE"), 0, 0, 0, 0),
          (t(9, 18, 31), "NSE_FNO:NIFTY:2026-11-24:25100:PE", 150.0, 151.0, 150.0, 5.0),                      # a later expiry: ignored
          (t(9, 18, 32), "NSE_FNO:NIFTY:2026-11-24", 25100.0, 25101.0, 25100.0, 5.0)]                         # the future: ignored
    R, cov = to_bars(pd.DataFrame(tk, columns=["t", "iid", "bid", "ask", "ltp", "oi"]), day, {(iid(25000, "CE"), 556): 75})
    assert len(R) == 2 and set(R.exp) == {exp}, R
    a = R[R.side == "CE"].iloc[0]   # 09:16 bar: mids 101, 105, 102.5 -> o 101 h 105 l 101 c 102.5; spot = last index ltp of the minute 25030 -> ATM 25050 -> off -1
    assert (a.m, a.o, a.h, a.l, a.c, a.oi, a.spot, a.off, a.strike, a.vol) == (556, 101.0, 105.0, 101.0, 102.5, 530.0, 25030.0, -1, 25000.0, 75), a
    assert a.ts == int(datetime(2026, 11, 12, 9, 16, tzinfo=IST).timestamp())
    b = R[R.side == "PE"].iloc[0]; assert (b.m, b.c, b.spot, b.off) == (558, 80.5, 25080.0, 0) and b.vol != b.vol, b   # 25080 -> ATM 25100 -> off 0; no volume given -> NaN
    T_ = (5 * 1440 + 930 - 558 - 1) / 525600; px = bs(25080.0, 25100.0, T_, 0.15, 0.065, "PE")                # IV round trip: a 15% option reads 15%
    assert abs(_iv(px, 25080.0, 25100.0, T_, "PE") - 15.0) < 0.01
    assert cov["NIFTY"]["first"] == "09:16" and cov["NIFTY"]["exp"] == exp and cov["NIFTY"]["full"] is False and cov["SENSEX"]["full"] is False and cov["NIFTY"]["bar"] == [25030.0, 25080.0, 25030.0, 25080.0]
    # tagger: Thursday 11-12 -> Tuesday 11-17 is 3 business days; gap = 25100 / 25000 - 1 = +0.40%; yesterday 24900 -> 25000 = +0.40%; ratio 0.9 calm
    g = tags(day, exp, [25100.0, 25200.0, 25050.0, 25150.0], [24900.0, 25050.0, 24850.0, 25000.0], 0.9)
    assert g == dict(dte="D2+", gap="GAP_UP", prev="PREV_UP", oriv="CALM"), g
    g = tags(exp, exp, [25000.0, 1, 1, 1], [25040.0, 1, 1, 25050.0], 1.2); assert g == dict(dte="D0", gap="GAP_FLAT", prev="PREV_FLAT", oriv="ACTIVE"), g   # -0.20% gap, +0.04% day
    assert tags(day, "2026-11-13", None, None, None) == dict(dte="D1", gap="NA", prev="NA", oriv="NA")
    assert [tod(x) for x in ("09:20", "09:46", "10:59", "11:00", "13:00", "15:10")] == ["09:15-09:45", "09:46-11:00", "09:46-11:00", "11:00-13:00", "13:00-15:30", "13:00-15:30"]
    assert describe([100.0, 110.0, 98.0, 107.0])["daytype"] == "TREND" and describe([100.0, 110.0, 98.0, 103.0])["daytype"] == "RANGE"   # 7 of 12 vs 3 of 12
    assert tdays_before("2026-11-09", 2, {"2026-11-06"}) == ["2026-11-05", "2026-11-04"]                       # Monday: skips the weekend and a Friday holiday
    assert hm(0) == "09:15" and hm(31) == "09:46"
    # shadow mapping: a no-signal day keeps the baseline straddle, logs FIN1 NO_SIGNAL and S2's own trade
    r = dict(sym="NIFTY", status="OK", straddle_pnl_inr=-500.0, pnl_inr=0.0, signal=False, s2_signal=True, s2_short_pnl_inr=300.0, s2_pnl_inr=300.0, s1_pnl_inr=300.0, lead_hist="OK", sc1_signal=False,
             b1_status="NO_HIST", ivs_status="GATE_OFF", xs_status="GATE_OFF", legs={"CE": {"expiry": exp}}, e33_trades=[dict(lead="S_CE", t_entry="10:01:02", pnl=120.0, why="tgt"), dict(lead="S_CE", status="NO_QUOTES")])
    m = {x["cell"]: x for x in shadow_cells(day, r)}
    assert (m["SH.LSTRAD"]["pnl"], m["SH.FIN1"]["status"], m["SH.S2"]["pnl"], m["SH.S2"]["trades"][0]["t"], m["SH.SC1"]["status"], m["SH.B1"]["status"], m["SH.IVS"]["status"]) == \
        (-500.0, "NO_SIGNAL", 300.0, "09:47", "NO_SIGNAL", "UNTESTABLE:NO_HIST", "NOT_EXPIRY"), m
    assert m["SH.E33_SCE"]["n"] == 1 and m["SH.E33_SCE"]["trades"][0]["t"] == "10:01" and m["SH.E33_LPE"]["status"] == "NO_SIGNAL" and m["SH.S1"]["wins"] == 1
    m = {x["cell"]: x for x in shadow_cells(day, dict(r, lead_hist="NO_HIST"))}   # no prior days: the history-fed leads are untestable, never traded on half a rule
    assert m["SH.SC1"]["status"] == m["SH.E33_SCE"]["status"] == m["SH.E33_LPE"]["status"] == "UNTESTABLE:NO_HIST" and m["SH.E33_SCE"]["n"] == 0 and m["SH.S1"]["n"] == 1
    # ledger: append-only and idempotent; an engine error is never stored
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "l.jsonl"; rows = [mk(day, "NIFTY", "SH.S1", [dict(t="09:47", pnl=100.0)]), mk(day, "NIFTY", "E39.S1", status="ENGINE_ERROR:X"), mk(day, "SENSEX", "SH.S1")]
        assert append(rows, fp) == 2 and append(rows, fp) == 0 and len(read_ledger(fp)) == 2
        assert append([mk(day, "NIFTY", "SH.S1", [dict(t="09:47", pnl=-999.0)]), mk(day, "NIFTY", "E39.S1", [dict(t="09:47", pnl=5.0)])], fp) == 1   # the logged row is kept; the errored one fills
        L = read_ledger(fp); assert len(L) == 3 and [x["pnl"] for x in L if x["cell"] == "SH.S1" and x["sym"] == "NIFTY"] == [100.0]
    # report maths: placebo and the learn rule on a built ledger (50 calm trades +100, 50 active trades -100 for one cell)
    assert _p_base([10.0, 10.0], [10.0] * 5) == 1.0 and _p_base([10.0, 10.0], [1.0] * 5) == 0.0 and _p_base([1.0] * 3, [1.0]) is None
    assert _p_twin([5.0] * 10) == 0.0 and _p_twin([-5.0] * 10) == 1.0
    # unit shuffle: 4 day-units worth -10, -10, +10, +10, the bucket = the first two: 1 of the 6 two-unit sets is as bad -> p = 1/6, however many trades sit inside a unit
    assert abs(_p_units([-10.0, -10.0, 10.0, 10.0], [True, True, False, False]) - 1 / 6) < 0.03 and _p_units([1.0, 2.0], [True, True]) is None
    assert abs(_p_within([-1.0, -1.0, -1.0]) - 1 / 8) < 0.03                                                    # 3 units all worse: 1 of the 8 sign patterns
    assert seen_until("E54.V1.ATM.3/2/60s") == "2026-11-16" and seen_until("E39.S1") == PANEL_END
    L = []
    for n in range(50):   # 50 days: above the 40-trade and 10-day floors. S2 (placebo = the ungated S1) wins on calm NIFTY, loses on active SENSEX
        d = (date(2027, 1, 4) + timedelta(n)).isoformat()
        for sym, orv, pnl in (("NIFTY", "CALM", 100.0), ("SENSEX", "ACTIVE", -100.0)):
            L.append(dict(day=d, sym=sym, cell="_DAY", status="FULL", seen=False, tags=dict(dte="D1", gap="GAP_FLAT", prev="PREV_FLAT", oriv=orv), desc={}))
            L.append(mk(d, sym, "SH.S2", [dict(t="09:47", pnl=pnl)])); L.append(mk(d, sym, "SH.S1", [dict(t="09:47", pnl=-50.0)])); L.append(mk(d, sym, "SH.B1", [dict(t="09:20", pnl=pnl)]))
            L.append(mk(d, sym, "E39.S1", [dict(t="09:47", pnl=pnl)]))   # the same split, but a cell with no placebo: it can never be proposed
    T = trades_frame(L); assert len(T) == 400 and set(T[T.cell == "SH.B1"].oriv) == {"PRE_0945"} and T.fwd.all() and not T.forced.any()   # a 09:20 entry cannot use the 09:45 tag
    lk, wa = learn(T); c = [(r["cell"], r["dim"], r["bucket"]) for r in lk if r["verdict"] == "CANDIDATE"]
    assert ("SH.S2", "oriv", "ACTIVE") in c and ("SH.S2", "oriv", "CALM") not in c and not any(x[0] == "E39.S1" for x in c) and not any(r["dim"] == "oriv" and r["cell"] == "SH.B1" for r in lk), c
    lk2, wa2 = learn(T[T.day < "2027-01-20"]); assert not lk2 and any(r["bucket"] == "ACTIVE" for r in wa2)     # 16 trades per bucket: WATCH only, never a candidate
    assert not learn(T.assign(day="2027-01-04"))[0]                                                               # 50 trades on ONE day: never looked at as a candidate
    assert not learn(T.assign(fwd=False))[0] and not learn(T.assign(fwd=False))[1] and not learn(T.assign(forced=True))[0]   # seen days and forced exits never feed the learn rule
    old = [dict(r, day="2026-10-29") for r in L[:5]] + [mk("2026-10-29", "SENSEX", "E54.V1.ATM.3/2/60s", [dict(t="10:00", pnl=1.0)]), mk("2026-11-17", "NIFTY", "E54.V1.ATM.3/2/60s", [dict(t="10:00", pnl=1.0, forced=True)])]
    To = trades_frame(old); assert To[To.cell == "E54.V1.ATM.3/2/60s"].fwd.tolist() == [False, True] and To[To.cell == "SH.S2"].fwd.all() and To.forced.tolist()[-1]   # 10-29 is an E54 discovery day, forward for the lab cells
    txt = report(L=L); assert "CANDIDATE: SH.S2 in oriv=ACTIVE" in txt and "forced%" in txt and "Bonferroni alpha" in txt
    sh_ = report(L=L, short=True); assert "cells have 20+ trades" in sh_ and "Nothing judgeable yet" in report(L=[r for r in L if r["day"] < "2027-01-06"], short=True)
    assert set(BASE) | set(BASE.values()) <= set(ROSTER) and all(a in ROSTER and b in ROSTER for a, b in PAIRS)
    # one broken engine block yields its fallback rows and a FAILED line, never an exception
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()) as o, contextlib.redirect_stderr(io.StringIO()): g_ = _guard("x", lambda: 1 / 0, lambda: ["fallback"])
    assert g_ == ["fallback"] and "fwd_bench FAILED x: ZeroDivisionError" in o.getvalue() and _guard("y", lambda: 5, lambda: None) == 5
    print("fwd_bench selftest OK (converter bar / spot / ATM offset / IV round trip / volume / dropped rows; tagger buckets; calendar; shadow mapping; "
          "append-only idempotent ledger; per-cell forward cutoff; unit-shuffle and sign-flip p known answers; learn rule on forward, unforced trades with a placebo-beating rest; "
          "short report judgeable-only; engine-failure guard)")


if __name__ == "__main__":
    a = sys.argv[1:]; cmd = a[0] if a else ""
    if cmd == "selftest": selftest()
    elif cmd == "day" and len(a) > 1: score_day(a[1], dry="--dry" in a, again="--again" in a)
    elif cmd == "backfill": backfill()
    elif cmd == "report": print(report(since=a[a.index("--since") + 1] if "--since" in a else None, short="--short" in a))
    elif cmd == "roster": print(roster())
    elif cmd == "check" and len(a) > 1: check(a[1])
    elif cmd == "_labs": _labs(a[1], a[2])
    else: print(__doc__); sys.exit(1)
