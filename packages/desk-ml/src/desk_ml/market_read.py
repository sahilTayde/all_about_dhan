"""Market read (2026-10-12): one dict per closed minute describing the market. LOG ONLY.

It never gates, sizes or places a trade. Schema: /workspace/dhan/desk/market_read_SCHEMA.md.
Any input that is absent, stale, or from a partial tape is "DATA_MISSING", never a guess.

Pieces:
- ``compute(bars, ctx, cross, chain, depth)``: pure function, last N closed 1-minute bars -> dict.
- ``day_context(day, underlying, daily)``: prior-day / prior-week levels, VIX percentile, expiry,
  15-day trend and opening-range median, from a daily table (``config/market_read/daily.json``).
- ``LiveLogger``: desk-loop hook (flag MARKET_READ_LOG=1). Builds minute bars from dual-tape snaps,
  reads the cross-market tape tails, appends to ``data/market_read/<day>/market_read.jsonl``.
- ``python -m desk_ml.market_read --history YYYY-MM-DD[,...]``: runs on base_1m for Research.

Python 3.9 compatible (legacy desk venv).
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DM = "DATA_MISSING"
IST = timezone(timedelta(hours=5, minutes=30))
HEAVY = ("HDFCBANK", "RELIANCE", "ICICIBANK", "INFY", "TCS", "BHARTIARTL", "LT", "ITC",
         "SBIN", "AXISBANK", "KOTAKBANK")
WINDOW = 120  # bars used for swings / order blocks (VWAP and OR use the whole session)
EXPIRY_WEEKDAY = {"NIFTY": 1, "SENSEX": 3}  # Tue / Thu (NSE/BSE weekly since Sep 2025)

Bar = Tuple[str, float, float, float, float]  # (HH:MM IST, o, h, l, c)


def _ok(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _r(x: Any, n: int = 2) -> Any:
    return round(float(x), n) if _ok(x) else DM


def _pct(a: Any, b: Any) -> Any:
    return round((a / b - 1.0) * 100.0, 3) if _ok(a) and _ok(b) and b else DM


# ---------------------------------------------------------------- price structure
def swings(bars: Sequence[Bar], k: int = 2) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """Fractal pivots: a high/low with k lower highs / higher lows on each side (confirmed bars only)."""
    hs, ls = [], []
    for i in range(k, len(bars) - k):
        h, l = bars[i][2], bars[i][3]
        if all(h > bars[j][2] for j in range(i - k, i + k + 1) if j != i):
            hs.append((i, h))
        if all(l < bars[j][3] for j in range(i - k, i + k + 1) if j != i):
            ls.append((i, l))
    return hs, ls


def trend_structure(hs: list, ls: list) -> Tuple[str, str]:
    if len(hs) < 2 or len(ls) < 2:
        return DM, DM
    hh, hl = hs[-1][1] > hs[-2][1], ls[-1][1] > ls[-2][1]
    if hh and hl:
        return "UP", "HH_HL"
    if not hh and not hl:
        return "DOWN", "LH_LL"
    return "SIDEWAYS", "MIXED"


def order_block(bars: Sequence[Bar]) -> Any:
    """Most recent order block: the last opposite candle before a 3-bar displacement that moves
    more than 2x the average bar range and closes beyond that candle's extreme."""
    if len(bars) < 10:
        return DM
    rng = sum(b[2] - b[3] for b in bars) / len(bars) or 1e-9
    for i in range(len(bars) - 4, 0, -1):
        o, h, l, c = bars[i][1:]
        end = bars[i + 3][4]
        if c < o and end - c > 2 * rng and end > h:
            return {"side": "BULL", "lo": _r(l), "hi": _r(h), "ts": bars[i][0]}
        if c > o and c - end > 2 * rng and end < l:
            return {"side": "BEAR", "lo": _r(l), "hi": _r(h), "ts": bars[i][0]}
    return "NONE"


def rejection(bar: Bar, levels: Sequence[float], tol: float) -> str:
    """Wick >= 2x body and >= half the bar, with the wick touching a level (within tol points)."""
    _, o, h, l, c = bar
    body, rng = abs(c - o), h - l
    if rng <= 0:
        return "NONE"
    lo_w, up_w = min(o, c) - l, h - max(o, c)
    near = lambda p: any(_ok(x) and abs(p - x) <= tol for x in levels)
    if lo_w >= 2 * body and lo_w >= rng / 2 and near(l):
        return "BULL_REJECT"
    if up_w >= 2 * body and up_w >= rng / 2 and near(h):
        return "BEAR_REJECT"
    return "NONE"


# ---------------------------------------------------------------- day context
def _daily_path(root: Optional[Path] = None) -> Path:
    env = os.environ.get("MARKET_READ_DAILY")
    if env:
        return Path(env)
    return (root or Path.cwd()) / "config" / "market_read" / "daily.json"


def load_daily(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def is_expiry(day: str, underlying: str) -> Any:
    from desk_ml import nse_calendar as cal
    try:
        d = date.fromisoformat(day)
        wd = EXPIRY_WEEKDAY.get(underlying.upper())
        if wd is None:
            return DM
        exp = d + timedelta(days=(wd - d.weekday()) % 7)
        while not cal.is_trading_day(exp):  # holiday -> previous trading day
            exp -= timedelta(days=1)
        return int(exp == d)
    except Exception:  # noqa: BLE001 - calendar year not covered
        return DM


def day_context(day: str, underlying: str, daily: Dict[str, Any], vix_prev_close: Any = None) -> Dict[str, Any]:
    """Levels known before the session opens. Partial or absent prior days -> DATA_MISSING."""
    from desk_ml import nse_calendar as cal
    ctx: Dict[str, Any] = {k: DM for k in ("pdh", "pdl", "pdc", "wk_hi", "wk_lo", "vixp", "vch", "tr15", "r15med")}
    ctx["expiry"] = is_expiry(day, underlying)
    rows = daily.get(underlying.upper()) or {}
    try:
        pday = cal.prior_trading_day(day)
    except Exception:  # noqa: BLE001
        return ctx
    p = rows.get(pday)
    if p and not p[4]:
        ctx["pdh"], ctx["pdl"], ctx["pdc"] = p[1], p[2], p[3]
    # prior completed ISO week high/low (all its trading days must be full)
    d = date.fromisoformat(day)
    mon = d - timedelta(days=d.weekday() + 7)
    wk = []
    full = True
    for i in range(5):
        x = (mon + timedelta(days=i)).isoformat()
        try:
            if not cal.is_trading_day(x):
                continue
        except Exception:  # noqa: BLE001
            full = False
            break
        r = rows.get(x)
        if not r or r[4]:
            full = False
            break
        wk.append(r)
    if full and wk:
        ctx["wk_hi"], ctx["wk_lo"] = max(r[1] for r in wk), min(r[2] for r in wk)
    # 15-day trend: prior close / close 16 trading days back (scenario_map tr15)
    prior = sorted(x for x in rows if x < day)
    if len(prior) >= 16 and not rows[prior[-1]][4] and prior[-1] == pday:
        ctx["tr15"] = rows[prior[-1]][3] / rows[prior[-16]][3] - 1
    r15 = [rows[x][5] for x in prior[-20:] if len(rows[x]) > 5 and _ok(rows[x][5])]
    if len(r15) >= 10:
        ctx["r15med"] = sorted(r15)[len(r15) // 2]
    # VIX: prior-day percentile over the 250 days before it, and prior-day change
    vix = dict(daily.get("INDIAVIX") or {})
    if pday not in vix and _ok(vix_prev_close):
        vix[pday] = float(vix_prev_close)  # Dhan prev-close packet = prior session's VIX close
    vd = sorted(x for x in vix if x <= pday)
    if vd and vd[-1] == pday and len(vd) >= 2:
        hist = [vix[x] for x in vd[-251:-1]]
        ctx["vixp"] = sum(1 for x in hist if x < vix[pday]) / len(hist)
        ctx["vch"] = vix[pday] / vix[vd[-2]] - 1
    return ctx


def classify_day(bars: Sequence[Bar], ctx: Dict[str, Any]) -> Any:
    """Existing desk 10:00 classifier (desk/playbook/build_stats.py dtype)."""
    if not bars or bars[-1][0] < "10:00":
        return "PENDING"
    first = [b for b in bars if "09:15" <= b[0] < "09:30"]
    vixp, vch, exp = ctx.get("vixp"), ctx.get("vch"), ctx.get("expiry")
    if not (_ok(vixp) and _ok(vch)):
        return DM
    if vixp >= 0.80 or vch >= 0.10:
        return "FEAR"
    if exp not in (0, 1):
        return DM
    if exp == 1:
        return "EXPIRY"
    if not first or first[0][0] != "09:15" or not _ok(ctx.get("pdc")):
        return DM
    gap = (first[0][1] / ctx["pdc"] - 1) * 100
    if abs(gap) >= 0.40:
        return "GAP_OPEN"
    if not _ok(ctx.get("r15med")):
        return DM
    r15 = max(b[2] for b in first) - min(b[3] for b in first)
    if r15 >= 1.5 * ctx["r15med"]:
        return "WIDE_OPEN"
    if not _ok(ctx.get("tr15")):
        return DM
    return "TREND_QUIET" if abs(ctx["tr15"]) > 0.02 else "FLAT_QUIET"


# ---------------------------------------------------------------- the read
def compute(bars: Sequence[Bar], ctx: Optional[Dict[str, Any]] = None, cross: Optional[Dict[str, Any]] = None,
            chain: Optional[Dict[str, Any]] = None, depth: Optional[Tuple[float, float]] = None,
            *, underlying: str = "NIFTY", day: str = "", source: str = "live") -> Dict[str, Any]:
    """bars: today's closed 1-minute bars (oldest first). cross: name -> {"open","last","last5"} (latest
    cross-market prints; INDIAVIX also "prev_close"). chain: {"pcr","maxpain","atm_iv"}. depth: (bid_qty, ask_qty)."""
    t0 = time.perf_counter()
    ctx, cross, chain = ctx or {}, cross or {}, chain or {}
    out: Dict[str, Any] = {"ts": f"{day}T{bars[-1][0]}:00+05:30" if bars else DM, "day": day,
                           "underlying": underlying, "source": source, "log_only": True}
    if not bars:
        out["missing"] = ["bars"]
        return out
    spot = bars[-1][4]
    win = list(bars[-WINDOW:])
    hs, ls = swings(win)
    out["spot"] = _r(spot)
    out["day_type"] = classify_day(bars, ctx)
    out["trend"], out["structure"] = trend_structure(hs, ls)
    tw = sum((b[2] + b[3] + b[4]) / 3 for b in bars) / len(bars)
    out["vwap"], out["vwap_kind"] = _r(tw), "TWAP_INDEX"  # ponytail: index has no volume; futures VWAP later
    out["vwap_dist"] = _r(spot - tw)
    for k in ("pdh", "pdl", "pdc", "wk_hi", "wk_lo"):
        out[k] = _r(ctx.get(k))
    first = [b for b in bars if "09:15" <= b[0] < "09:30"]
    if bars[-1][0] >= "09:30" and first and first[0][0] == "09:15":
        out["or_hi"], out["or_lo"] = _r(max(b[2] for b in first)), _r(min(b[3] for b in first))
    else:
        out["or_hi"] = out["or_lo"] = DM
    out["order_block"] = order_block(win)
    above = [h for _, h in hs if h > spot] + [x for x in (ctx.get("pdh"), ctx.get("wk_hi")) if _ok(x) and x > spot]
    below = [l for _, l in ls if l < spot] + [x for x in (ctx.get("pdl"), ctx.get("wk_lo")) if _ok(x) and x < spot]
    out["liq_zone"] = {"above": _r(min(above)) if above else DM, "below": _r(max(below)) if below else DM}
    levels = [x for x in (out["pdh"], out["pdl"], out["or_hi"], out["or_lo"], tw) if _ok(x)]
    levels += [h for _, h in hs[-3:]] + [l for _, l in ls[-3:]]
    out["rejection"] = rejection(bars[-1], levels, tol=max(spot * 0.0005, 1.0))
    if depth and _ok(depth[0]) and _ok(depth[1]) and depth[0] + depth[1] > 0:
        out["depth_imb"] = round((depth[0] - depth[1]) / (depth[0] + depth[1]), 3)
    else:
        out["depth_imb"] = DM
    bnf = cross.get("BANKNIFTY") or {}
    if len(bars) >= 6 and _ok(bnf.get("last")) and _ok(bnf.get("last5")):
        a, b = spot - bars[-6][4], bnf["last"] - bnf["last5"]
        out["bnf_agree"] = (a > 0) == (b > 0) if a and b else "FLAT"
    else:
        out["bnf_agree"] = DM
    up = dn = n = 0
    for s in HEAVY:
        q = cross.get(s) or {}
        if _ok(q.get("open")) and _ok(q.get("last")):
            n += 1
            up += q["last"] > q["open"]
            dn += q["last"] < q["open"]
    out["heavy_breadth"] = {"up": up, "down": dn, "of": n} if n else DM
    v = cross.get("INDIAVIX") or {}
    out["vix"] = _r(v.get("last"))
    out["vix_chg"] = _pct(v.get("last"), v.get("prev_close"))
    for k, name in (("crude_chg", "CRUDEOIL"), ("gold_chg", "GOLD"), ("usdinr_chg", "USDINR")):
        q = cross.get(name) or {}
        out[k] = _pct(q.get("last"), q.get("open"))
    out["pcr"] = _r(chain.get("pcr"), 3)
    out["maxpain"] = _r(chain.get("maxpain"))
    out["atm_iv"] = _r(chain.get("atm_iv"))
    out["gift_global"] = DM  # no free real-time GIFT Nifty / global feed wired
    out["missing"] = sorted(k for k, x in out.items() if x == DM or (isinstance(x, dict) and DM in x.values()))
    out["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 3)
    return out


# ---------------------------------------------------------------- live hook
def _tail_rows(path: Path, nbytes: int = 65536) -> List[dict]:
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            start = max(0, fh.tell() - nbytes)
            fh.seek(start)
            lines = fh.read().splitlines()[1 if start else 0:]
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass
    return out


def _first_row(path: Path) -> Optional[dict]:
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.readline())
    except (OSError, ValueError):
        return None


class LiveLogger:
    """Feed it every dual-tape tick; it computes once per closed minute and appends one line per
    underlying. Never raises to the caller (``on_tick`` swallows), never touches orders."""

    def __init__(self, repo_root: Path, *, underlyings: Sequence[str] = ("NIFTY", "SENSEX")) -> None:
        self.root = Path(repo_root)
        self.unds = tuple(underlyings)
        self.bars: Dict[str, List[list]] = {u: [] for u in self.unds}
        self.ctx: Dict[str, Dict[str, Any]] = {}
        self.day = ""
        self.daily = load_daily(_daily_path(self.root))
        self.cross_root = Path(os.environ.get("MARKET_READ_CROSS_TAPE", str(self.root / "data" / "tape" / "cross")))
        self.v2_root = Path(os.environ.get("MARKET_READ_V2_TAPE", str(self.root / "data" / "tape" / "v2")))
        self.chain: Dict[str, Dict[str, Any]] = {}
        self.last_read: Dict[str, str] = {}

    def on_tick(self, snaps: Sequence[Any], now: Optional[datetime] = None) -> List[dict]:
        try:
            return self._on_tick(snaps, now or datetime.now(IST))
        except Exception as exc:  # noqa: BLE001 - log-only module must never break the loop
            try:
                self._append({"ts": (now or datetime.now(IST)).isoformat(), "error": f"{type(exc).__name__}: {exc}"[:300]})
            except Exception:  # noqa: BLE001,S110
                pass
            return []

    def _on_tick(self, snaps: Sequence[Any], now: datetime) -> List[dict]:
        now = now.astimezone(IST)
        day, m = now.date().isoformat(), now.strftime("%H:%M")
        if day != self.day:
            self.day, self.ctx, self.last_read = day, {}, {}
            self.bars = {u: [] for u in self.unds}
        done: List[dict] = []
        for s in snaps:
            d = s.to_dict() if hasattr(s, "to_dict") else dict(s)
            u = str(d.get("underlying") or "").upper()
            if u not in self.bars:
                continue
            px = d.get("index_ltp")
            stale = d.get("stale") or "carry" in str(d.get("index_source") or "")
            self.chain[u] = {"pcr": d.get("pcr_oi"), "maxpain": None,
                             "atm_iv": _avg(d.get("atm_ce_iv"), d.get("atm_pe_iv"))}
            bl = self.bars[u]
            if bl and bl[-1][0] < m and self.last_read.get(u) != bl[-1][0]:  # minute closed -> one read
                self.last_read[u] = bl[-1][0]
                done.append(self._read(u, day))
            if not _ok(px) or stale or not ("09:15" <= m <= "15:29"):
                continue
            px = float(px)
            if bl and bl[-1][0] == m:
                b = bl[-1]
                b[2], b[3], b[4] = max(b[2], px), min(b[3], px), px
            else:
                bl.append([m, px, px, px, px])
            del bl[:-400]
        for r in done:
            self._append(r)
        return done

    def _read(self, u: str, day: str) -> dict:
        closed = [tuple(b) for b in self.bars[u]]  # called before the new minute's bar exists
        cross = self._cross(day)
        if u not in self.ctx:
            self.ctx[u] = day_context(day, u, self.daily, (cross.get("INDIAVIX") or {}).get("prev_close"))
        out = compute(closed, self.ctx[u], cross, self.chain.get(u), self._depth(day, u), underlying=u, day=day, source="live")
        return out

    def _cross(self, day: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not self.cross_root.is_dir():
            return out
        for p in self.cross_root.glob(f"*/{day}.jsonl"):
            rows = _tail_rows(p, 8192)
            first = _first_row(p)
            if not rows or not first:
                continue
            last = rows[-1]
            five = rows[-6] if len(rows) >= 6 else None
            out[p.parent.name] = {"open": first.get("o"), "last": last.get("c"), "prev_close": last.get("prev_close"),
                                  "last5": five.get("c") if five else None}
        return out

    def _depth(self, day: str, u: str) -> Optional[Tuple[float, float]]:
        """Top-5 bid/ask qty of the current-month index future from the V2 research_quotes tail."""
        rows = _tail_rows(self.v2_root / day / "research_quotes.jsonl", 32768)
        key = ("NSE_FNO:NIFTY:" if u == "NIFTY" else "BSE_FNO:SENSEX:")
        for r in reversed(rows):
            p = r.get("payload") or {}
            if str(p.get("instrument_id", "")).startswith(key):
                lv = p.get("levels") or {}
                b = sum(q for _, q in lv.get("bid") or [])
                a = sum(q for _, q in lv.get("ask") or [])
                return (float(b), float(a)) if a + b > 0 else None
        return None

    def _append(self, row: dict) -> None:
        p = self.root / "data" / "market_read" / (self.day or "unknown") / "market_read.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")


def _avg(a: Any, b: Any) -> Any:
    xs = [float(x) for x in (a, b) if _ok(x)]
    return sum(xs) / len(xs) if xs else None


_LOGGER: Optional[LiveLogger] = None


def log_pass(repo_root: Path, snaps: Sequence[Any]) -> None:
    """Desk-loop entry point. Caller checks MARKET_READ_LOG=1 and wraps in try/except."""
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = LiveLogger(repo_root)
    _LOGGER.on_tick(snaps)


# ---------------------------------------------------------------- history (base_1m)
BASE_1M = Path(os.environ.get("MARKET_READ_BASE_1M", "/workspace/dhan/output/lab_round7b/base_1m.parquet"))


def daily_from_base(M: Any) -> Dict[str, Any]:
    """NIFTY daily rows [o,h,l,c,partial,r15] from base_1m (a day is partial if it lacks 09:15 or 15:29)."""
    rows: Dict[str, Any] = {}
    for d, g in M.groupby("day", sort=True):
        mm = g.m.values
        first = g[(g.m >= 555) & (g.m < 570)]
        partial = not (mm.min() <= 555 and mm.max() >= 929)
        rows[str(d)] = [float(g.open.iloc[0]), float(g.high.max()), float(g.low.min()), float(g.close.iloc[-1]),
                        bool(partial), float(first.high.max() - first.low.min()) if len(first) else None]
    return rows


def history(days: Sequence[str], every: int = 1) -> List[dict]:
    import pandas as pd
    M = pd.read_parquet(BASE_1M, columns=["day", "m", "open", "high", "low", "close", "bnf", "dte"])
    M["day"] = M.day.astype(str)
    daily = {"NIFTY": daily_from_base(M), "INDIAVIX": {}}
    vx = Path(os.environ.get("MARKET_READ_VIX_CSV", "/workspace/dhan/research/lab/data_ext/daily_INDIAVIX.csv"))
    if vx.exists():
        for ln in vx.read_text().splitlines()[1:]:
            p = ln.split(",")
            if len(p) >= 5 and p[4]:
                daily["INDIAVIX"][p[0][:10]] = float(p[4])
    out = []
    for d in days:
        g = M[M.day == d]
        if g.empty:
            out.append({"day": d, "error": "DATA_MISSING: day not in base_1m"})
            continue
        ctx = day_context(d, "NIFTY", daily)
        ctx["expiry"] = int(g.dte.iloc[0] == 0)  # base_1m carries the true expiry calendar
        bars: List[Bar] = []
        bnf = list(g.bnf.values)
        for i, r in enumerate(g.itertuples()):
            bars.append((f"{int(r.m) // 60:02d}:{int(r.m) % 60:02d}", float(r.open), float(r.high), float(r.low), float(r.close)))
            if i % every:
                continue
            cross = {}
            if i >= 5 and _ok(bnf[i]) and _ok(bnf[i - 5]):
                cross["BANKNIFTY"] = {"last": float(bnf[i]), "last5": float(bnf[i - 5]), "open": float(bnf[0])}
            out.append(compute(bars, ctx, cross, underlying="NIFTY", day=d, source="base_1m"))
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m desk_ml.market_read")
    ap.add_argument("--history", required=True, help="comma-separated YYYY-MM-DD days in base_1m")
    ap.add_argument("--out", type=Path, help="write jsonl here (default stdout)")
    a = ap.parse_args(argv)
    rows = history(a.history.split(","))
    text = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n"
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
