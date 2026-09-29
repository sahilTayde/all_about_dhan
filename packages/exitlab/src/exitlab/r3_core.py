"""Minute paths, GOOD_EXIT labels, and no-look-ahead features. Paper only."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

from exitlab.clock import IST, as_ist
from exitlab.fills import DEFAULT_SPREAD_PTS
from exitlab.tapes import spread_pts_for, strike_ltp, wing_ltp
from exitlab.types import Bar, Entry, Quote

SQUARE = time(15, 15)
HALF_SPREAD_MULT = 1.5


@dataclass
class Minute:
    """One IST minute on the entry's fixed strike. ltp is None on a hole."""

    ts: datetime
    available_ts: datetime
    ltp: float | None
    index: float | None = None
    volume: float | None = None
    oi: float | None = None
    iv: float | None = None
    opp_ltp: float | None = None
    spread: float | None = None
    bid: float | None = None
    ask: float | None = None
    hole: bool = False


@dataclass
class FeatRow:
    entry_id: str
    entry_set: str
    session: str
    side: str
    i: int
    ts: str
    label_5: str
    label_15: str
    label_30: str
    label_eod: str
    feats: dict[str, float | None] = field(default_factory=dict)


def half_spread_pts(moneyness: str, table: dict[str, float] | None = None) -> float:
    return spread_pts_for(moneyness, table or DEFAULT_SPREAD_PTS) / 2.0


def _floor_minute(ts: datetime) -> datetime:
    t = as_ist(ts)
    return t.replace(second=0, microsecond=0)


def live_minutes(entry: Entry, ticks: list[dict[str, Any]]) -> list[Minute]:
    """Resample dual-tape ticks to 1m on the FIXED strike. Missing strike = hole."""
    by: dict[datetime, dict[str, Any]] = {}
    for t in ticks:
        avail = as_ist(t["available_ts"])
        if avail < as_ist(entry.ts):
            continue
        if avail.time() >= time(15, 30):
            continue
        key = _floor_minute(avail)
        ltp = strike_ltp(t, side=entry.side, strike=entry.strike)
        opp = strike_ltp(t, side="PE" if entry.side == "CE" else "CE", strike=entry.strike)
        if opp is None:
            opp = wing_ltp(t, side="PE" if entry.side == "CE" else "CE", strike=entry.strike)
        empty = {"avail": avail, "ltp": None, "index": None, "opp": None, "iv": None}
        cell = by.setdefault(key, empty)
        cell["avail"] = avail
        if ltp is not None:
            cell["ltp"] = ltp
        if t.get("index") is not None:
            cell["index"] = t.get("index")
        if opp is not None:
            cell["opp"] = opp
        iv_key = "atm_ce_iv" if entry.side == "CE" else "atm_pe_iv"
        if t.get(iv_key) is not None:
            cell["iv"] = t.get(iv_key)
    keys = sorted(by)
    out: list[Minute] = []
    spread = spread_pts_for(entry.moneyness)
    for key in keys:
        cell = by[key]
        ltp = cell["ltp"]
        out.append(
            Minute(
                ts=key,
                available_ts=cell["avail"],
                ltp=None if ltp is None else float(ltp),
                index=None if cell["index"] is None else float(cell["index"]),
                iv=None if cell["iv"] is None else float(cell["iv"]),
                opp_ltp=None if cell["opp"] is None else float(cell["opp"]),
                spread=spread,
                hole=ltp is None,
            )
        )
    return out


def hist_minutes(entry: Entry, opt: list[Bar], index: list[Bar]) -> list[Minute]:
    """1m option path for the fixed strike. Empty path if the contract is missing."""
    side = entry.side.upper()
    opp_side = "PE" if side == "CE" else "CE"
    own = [
        b
        for b in opt
        if b.side == side
        and b.strike is not None
        and abs(float(b.strike) - float(entry.strike)) < 1e-6
        and as_ist(b.ts).date().isoformat() == entry.session
        and as_ist(b.available_ts) >= as_ist(entry.ts)
    ]
    opp = {
        as_ist(b.ts).replace(second=0, microsecond=0): b.close
        for b in opt
        if b.side == opp_side
        and b.strike is not None
        and abs(float(b.strike) - float(entry.strike)) < 1e-6
        and as_ist(b.ts).date().isoformat() == entry.session
    }
    idx = {
        as_ist(b.ts).replace(second=0, microsecond=0): b.close
        for b in index
        if as_ist(b.ts).date().isoformat() == entry.session
    }
    spread = spread_pts_for(entry.moneyness)
    out: list[Minute] = []
    for b in own:
        key = as_ist(b.ts).replace(second=0, microsecond=0)
        out.append(
            Minute(
                ts=key,
                available_ts=as_ist(b.available_ts),
                ltp=float(b.close),
                index=idx.get(key),
                volume=b.volume,
                oi=b.oi,
                opp_ltp=opp.get(key),
                spread=spread,
                hole=False,
            )
        )
    out.sort(key=lambda m: m.available_ts)
    return out


def minutes_to_series(minutes: list[Minute]) -> tuple[list[Quote], list[Bar]]:
    """Quotes + 1m bars. Holes are omitted (no other-strike mark)."""
    quotes: list[Quote] = []
    bars: list[Bar] = []
    for m in minutes:
        if m.ltp is None or m.ltp <= 0:
            continue
        quotes.append(
            Quote(
                available_ts=m.available_ts,
                bid=m.bid,
                ask=m.ask,
                ltp=m.ltp,
                index=m.index,
                iv=m.iv,
                strike=None,
                spread=m.spread,
                volume=m.volume,
                oi=m.oi,
                source="r3_minute",
            )
        )
        bars.append(
            Bar(
                ts=m.ts,
                available_ts=m.available_ts,
                open=m.ltp,
                high=m.ltp,
                low=m.ltp,
                close=m.ltp,
                volume=m.volume,
                oi=m.oi,
                index_close=m.index,
            )
        )
    return quotes, bars


def label_window(closes: list[float | None], *, horizon: int, half_spread: float) -> list[str]:
    """GOOD_EXIT = local peak, prominence >= 1.5 * half-spread, no higher later in window.

    Hindsight only. `horizon` is minutes ahead; use a large number for EOD.
    """
    n = len(closes)
    out = ["HOLD"] * n
    floor = HALF_SPREAD_MULT * float(half_spread)
    for i, px in enumerate(closes):
        if px is None:
            continue
        end = n if horizon >= n else min(n, i + 1 + horizon)
        later: list[float] = []
        for j in range(i + 1, end):
            cj = closes[j]
            if cj is not None:
                later.append(cj)
        if later and max(later) > px + 1e-12:
            continue
        prev = next((closes[j] for j in range(i - 1, -1, -1) if closes[j] is not None), None)
        if prev is not None and px + 1e-12 < prev:
            continue
        look: list[float] = []
        for j in range(max(0, i - 3), i + 1):
            cj = closes[j]
            if cj is not None:
                look.append(cj)
        trough = min(look) if look else float(px)
        if px - trough + 1e-12 < floor:
            continue
        out[i] = "GOOD_EXIT"
    return out


def labels_for(minutes: list[Minute], *, half_spread: float) -> dict[str, list[str]]:
    closes = [m.ltp for m in minutes]
    n = max(1, len(closes))
    return {
        "5": label_window(closes, horizon=5, half_spread=half_spread),
        "15": label_window(closes, horizon=15, half_spread=half_spread),
        "30": label_window(closes, horizon=30, half_spread=half_spread),
        "eod": label_window(closes, horizon=n, half_spread=half_spread),
    }


def _ret(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return (a - b) / b


def features_before(
    minutes: list[Minute],
    i: int,
    *,
    entry: Entry,
    day_index: list[float],
    regime: str,
    expiry: bool,
) -> dict[str, float | None]:
    """Features from minutes[:i] only. Minute i (and later) is invisible."""
    prior = minutes[:i]
    known = [m for m in prior if m.ltp is not None]
    if not known:
        return {}
    now = known[-1]
    px = float(now.ltp or 0.0)
    entry_px = float(entry.entry_price)
    peak = max(float(m.ltp or px) for m in known)
    trough = min(float(m.ltp or px) for m in known)
    closes = [float(m.ltp) for m in known if m.ltp is not None]
    highs_run = 0
    for m in reversed(known):
        if m.ltp is None:
            continue
        if float(m.ltp) + 1e-12 >= peak - 1e-9:
            break
        highs_run += 1
    mom: dict[int, float | None] = {}
    for n in (1, 3, 5, 10):
        if len(closes) > n:
            mom[n] = closes[-1] - closes[-1 - n]
        else:
            mom[n] = None
    body = None
    wick = None
    if len(closes) >= 2:
        body = abs(closes[-1] - closes[-2])
        wick = abs(max(closes[-2:]) - min(closes[-2:]))
    rngs = [abs(closes[j] - closes[j - 1]) for j in range(1, len(closes))]
    expand = None
    if len(rngs) >= 4:
        expand = (sum(rngs[-2:]) / 2.0) / (sum(rngs[-4:-2]) / 2.0 + 1e-9)
    vol_chg = None
    oi_chg = None
    if len(known) >= 2:
        v0, v1 = known[-2].volume, known[-1].volume
        o0, o1 = known[-2].oi, known[-1].oi
        if v0 and v1:
            vol_chg = v1 - v0
        if o0 and o1:
            oi_chg = o1 - o0
    idx_known = [m.index for m in prior if m.index is not None]
    idx_now = idx_known[-1] if idx_known else None
    idx_1 = idx_known[-1] - idx_known[-2] if len(idx_known) >= 2 else None
    idx_5 = idx_known[-1] - idx_known[-6] if len(idx_known) >= 6 else None
    idx_15 = idx_known[-1] - idx_known[-16] if len(idx_known) >= 16 else None
    vwap = (sum(day_index) / len(day_index)) if day_index else None
    d_high = None
    d_low = None
    if day_index and idx_now is not None:
        d_high = idx_now - max(day_index)
        d_low = idx_now - min(day_index)
    first30 = day_index[:30] if day_index else []
    fh_hi = max(first30) if first30 else None
    fh_lo = min(first30) if first30 else None
    fh_break = None
    if fh_hi is not None and fh_lo is not None and idx_now is not None and len(day_index) >= 30:
        if idx_now > fh_hi:
            fh_break = 1.0
        elif idx_now < fh_lo:
            fh_break = -1.0
        else:
            fh_break = 0.0
    round100 = None
    round50 = None
    if idx_now is not None:
        round100 = idx_now - round(idx_now / 100.0) * 100.0
        round50 = idx_now - round(idx_now / 50.0) * 50.0
    t_now = as_ist(now.available_ts)
    mins_to_sq = (datetime.combine(t_now.date(), SQUARE, tzinfo=IST) - t_now).total_seconds() / 60.0
    ivs = [m.iv for m in known if m.iv is not None]
    iv_chg = (ivs[-1] - ivs[0]) if len(ivs) >= 2 else None
    opp = [m.opp_ltp for m in known if m.opp_ltp is not None]
    opp_mom3 = (opp[-1] - opp[-4]) if len(opp) >= 4 else None
    delta_proxy = None
    if idx_1 is not None and mom[1] is not None and abs(idx_1) >= 0.5:
        delta_proxy = mom[1] / idx_1
    tod = t_now.hour * 60 + t_now.minute
    lower_highs = 0
    if len(closes) >= 5:
        window = closes[-5:]
        lower_highs = sum(1 for j in range(1, len(window)) if window[j] < window[j - 1])
    return {
        "ret_since_entry": _ret(px, entry_px),
        "pts_since_entry": px - entry_px,
        "peak_dd": (px - peak) / peak if peak else None,
        "peak_dd_pts": px - peak,
        "range_from_trough": px - trough,
        "mom_1": mom[1],
        "mom_3": mom[3],
        "mom_5": mom[5],
        "mom_10": mom[10],
        "body": body,
        "wick": wick,
        "body_wick": (body / wick) if body is not None and wick and wick > 1e-9 else None,
        "range_expand": expand,
        "mins_since_high": float(highs_run),
        "vol_chg": vol_chg,
        "oi_chg": oi_chg,
        "idx_1": idx_1,
        "idx_5": idx_5,
        "idx_15": idx_15,
        "dist_vwap": (idx_now - vwap) if idx_now is not None and vwap is not None else None,
        "dist_high": d_high,
        "dist_low": d_low,
        "fh_break": fh_break,
        "round100": round100,
        "round50": round50,
        "moneyness_pts": (entry.strike - (entry.atm_strike or entry.strike))
        * (1.0 if entry.side == "CE" else -1.0),
        "mins_to_1515": mins_to_sq,
        "expiry": 1.0 if expiry else 0.0,
        "iv_chg": iv_chg,
        "spread": now.spread,
        "tod_min": float(tod),
        "regime_trend": 1.0 if "trend" in regime else 0.0,
        "regime_chop": 1.0 if "chop" in regime else 0.0,
        "opp_mom3": opp_mom3,
        "delta_proxy": delta_proxy,
        "lower_highs_4": float(lower_highs),
        "age_min": (t_now - as_ist(entry.ts)).total_seconds() / 60.0,
        "ce": 1.0 if entry.side == "CE" else 0.0,
    }


def day_index_closes(minutes: list[Minute], *, upto: datetime | None = None) -> list[float]:
    out: list[float] = []
    for m in minutes:
        if m.index is None:
            continue
        if upto is not None and as_ist(m.available_ts) > as_ist(upto):
            break
        out.append(float(m.index))
    return out


def first30_regime(index_closes: list[float]) -> str:
    if len(index_closes) < 8:
        return "unknown"
    window = index_closes[:30] if len(index_closes) >= 30 else index_closes
    span = max(window) - min(window)
    net = window[-1] - window[0]
    if span < 1e-9:
        return "chop"
    er = abs(net) / span
    if er >= 0.55:
        return "trend_up" if net > 0 else "trend_down"
    return "chop"


def oracle_best_net(
    minutes: list[Minute],
    entry: Entry,
    *,
    charges_fn: Any,
    half_spread: float,
) -> dict[str, float | None]:
    """Hindsight best exit: max (ltp - half_spread) after entry. Not a trade signal."""
    best_px = None
    best_i = None
    for i, m in enumerate(minutes):
        if m.ltp is None:
            continue
        sell = float(m.ltp) - half_spread
        if best_px is None or sell > best_px:
            best_px = sell
            best_i = i
    if best_px is None:
        return {"oracle_px": None, "oracle_gross": None, "oracle_min": None}
    qty = entry.qty
    gross = (best_px - entry.entry_price) * qty
    return {
        "oracle_px": best_px,
        "oracle_gross": gross,
        "oracle_min": float(best_i or 0),
    }


def mfe_mae(minutes: list[Minute], entry: Entry) -> dict[str, float | None]:
    entry_px = entry.entry_price
    mfe = mae = None
    t_mfe = t_mae = None
    for i, m in enumerate(minutes):
        if m.ltp is None:
            continue
        d = float(m.ltp) - entry_px
        if mfe is None or d > mfe:
            mfe, t_mfe = d, float(i)
        if mae is None or d < mae:
            mae, t_mae = d, float(i)
    return {"mfe_pts": mfe, "mae_pts": mae, "mfe_min": t_mfe, "mae_min": t_mae}


def clock_bucket(ts: datetime, *, expiry: bool) -> str:
    t = as_ist(ts).time()
    if time(9, 15) <= t < time(9, 30):
        return "open_0915_0930"
    if time(11, 25) <= t < time(11, 40):
        return "mid_1130"
    if time(13, 25) <= t < time(13, 40):
        return "eu_1330"
    if expiry and time(14, 30) <= t < time(15, 15):
        return "expiry_1430_1515"
    if time(15, 15) <= t < time(15, 29):
        return "freeze_1515_1528"
    return "other"


def shift_minutes(minutes: list[Minute], *, seed: int) -> list[Minute]:
    """Shuffle future tail after the first third. Features before the cut must not change."""
    if len(minutes) < 6:
        return list(minutes)
    cut = max(2, len(minutes) // 3)
    head = minutes[:cut]
    tail = list(minutes[cut:])
    rng_i = seed % max(1, len(tail))
    tail = tail[rng_i:] + tail[:rng_i]
    return head + tail
