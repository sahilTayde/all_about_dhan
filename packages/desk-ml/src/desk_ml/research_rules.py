"""Frozen roster paper rules on the dual-tape loop. Log-only. No broker.

R01 PDIV_5|ALL|H20, R01_B3A_VOL (R01 + rv30 >= cut), R02 MOM_3_0.0005|ALL|H20.
Signal on minute t; fill = ATM premium in minute t+1; hold 20 min; TIME exit.
One open per rule per underlying. Execution stays refused.

Flag: PAPER_RESEARCH_RULES=1 (default on) / 0 to disable.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from desk_ml.groww_costs import groww_round_trip_charges, net_pnl_inr
from desk_ml.paper_lots import pnl_inr
from desk_ml.persist import repo_root
from desk_ml.tape import dual_tape_dir, parse_ts

IST = timezone(timedelta(hours=5, minutes=30))
FLAG_ENV = "PAPER_RESEARCH_RULES"

R01 = "R01_PDIV_5_ALL_H20"
R01_B3A = "R01_B3A_VOL"
R02 = "R02_MOM_3_0.0005_ALL_H20"
RULE_IDS = (R01, R01_B3A, R02)

# Frozen 2026-10-09 medians (scenarios.py VOL_CUT). Population rv30 gate.
VOL_CUT = {"NIFTY": 0.00021620371, "SENSEX": 0.00021971343}
RV30_LOOKBACK = 30
RV30_MIN_OBS = 20

FROZEN_RULES: tuple[dict[str, Any], ...] = (
    {
        "rule_id": R01,
        "source_config": "PDIV_5|ALL|H20",
        "family": "PDIV",
        "params": {"k": 5, "flat_thr": 0.0005, "dv_thr": 0.1},
        "regime_filter": "ALL",
        "hold_min": 20,
    },
    {
        "rule_id": R01_B3A,
        "source_config": "PDIV_5|ALL|H20|B3A_VOL",
        "family": "PDIV",
        "params": {"k": 5, "flat_thr": 0.0005, "dv_thr": 0.1},
        "regime_filter": "ALL",
        "hold_min": 20,
        "vol_gate": True,
    },
    {
        "rule_id": R02,
        "source_config": "MOM_3_0.0005|ALL|H20",
        "family": "MOM",
        "params": {"k": 3, "thr": 0.0005},
        "regime_filter": "ALL",
        "hold_min": 20,
    },
)

# Dual-tape already gathers SENSEX; 10 lots each. NIFTY 65, SENSEX 20 (roster).
UNDERLYINGS = ("NIFTY", "SENSEX")
LOTS = 10
LOT_SIZE = {"NIFTY": 65, "SENSEX": 20}
QTY = {name: LOTS * size for name, size in LOT_SIZE.items()}

SIGNAL_START = (9, 30)
SIGNAL_END = (14, 50)
WARMUP_MIN = 30


def enabled(environ: Optional[dict[str, str]] = None) -> bool:
    env = environ if environ is not None else os.environ
    raw = str(env.get(FLAG_ENV, "1")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def mplus(hhmm: str, n: int) -> str:
    hour, minute = (int(p) for p in hhmm.split(":"))
    total = hour * 60 + minute + int(n)
    return f"{total // 60:02d}:{total % 60:02d}"


def _num(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(val) or val <= 0:
        return None
    return val


def mid_or_ltp(bid: Any, ask: Any, ltp: Any) -> Optional[float]:
    """V2/research premium: mid when bid+ask exist, else LTP."""
    buy = _num(bid)
    sell = _num(ask)
    if buy is not None and sell is not None:
        return (buy + sell) / 2.0
    return _num(ltp)


def _wing_cell(wings: dict[str, Any], strike: float) -> dict[str, Any]:
    if not isinstance(wings, dict):
        return {}
    keys = (str(int(strike)) if float(strike) == int(strike) else str(strike), str(strike), f"{strike:.1f}")
    for key in keys:
        cell = wings.get(key)
        if isinstance(cell, dict):
            return cell
    return {}


def strike_premium(bar: dict[str, Any], side: str, strike: float) -> Optional[float]:
    cell = _wing_cell(bar.get("wings") or {}, strike)
    if side == "CE":
        px = mid_or_ltp(cell.get("ce_bid"), cell.get("ce_ask"), cell.get("ce"))
    else:
        px = mid_or_ltp(cell.get("pe_bid"), cell.get("pe_ask"), cell.get("pe"))
    if px is not None:
        return px
    atm = _num(bar.get("atm"))
    if atm is not None and abs(atm - float(strike)) < 1e-6:
        return _num(bar["ce"] if side == "CE" else bar["pe"])
    return None


def pdiv_side(
    *,
    idx_t: float,
    idx_k: float,
    ce_t: float,
    ce_k: float,
    pe_t: float,
    pe_k: float,
    flat_thr: float,
    dv_thr: float,
) -> Optional[str]:
    if any(v is None or v <= 0 for v in (idx_t, idx_k, ce_t, ce_k, pe_t, pe_k)):
        return None
    if abs(idx_t / idx_k - 1.0) >= float(flat_thr):
        return None
    dv = ce_t / ce_k - pe_t / pe_k
    if dv >= float(dv_thr):
        return "CE"
    if dv <= -float(dv_thr):
        return "PE"
    return None


def mom_side(*, idx_t: float, idx_k: float, thr: float) -> Optional[str]:
    if idx_t is None or idx_k is None or idx_t <= 0 or idx_k <= 0:
        return None
    ret = idx_t / idx_k - 1.0
    if ret >= float(thr):
        return "CE"
    if ret <= -float(thr):
        return "PE"
    return None


def rv30(bars: dict[str, dict[str, Any]], t: str) -> Optional[float]:
    """Population std of 1-minute log index returns on observed minutes in [t-30, t].

    Same formula as research scenarios.py. Needs >= 20 observed index prints; else None.
    """
    vals: list[float] = []
    for j in range(RV30_LOOKBACK, -1, -1):
        bar = bars.get(mplus(t, -j))
        if not bar:
            continue
        idx = _num(bar.get("idx"))
        if idx is None:
            continue
        vals.append(idx)
    if len(vals) < RV30_MIN_OBS:
        return None
    rets = [math.log(vals[i] / vals[i - 1]) for i in range(1, len(vals))]
    mean = sum(rets) / len(rets)
    return math.sqrt(sum((x - mean) ** 2 for x in rets) / len(rets))


def vol_gate_ok(rv: Optional[float], cut: Optional[float]) -> bool:
    return rv is not None and cut is not None and rv >= float(cut)


def signal(
    rule: dict[str, Any],
    bars: dict[str, dict[str, Any]],
    t: str,
    *,
    underlying: Optional[str] = None,
) -> Optional[str]:
    params = rule["params"]
    k = int(params["k"])
    past = mplus(t, -k)
    now = bars.get(t)
    then = _bar_near(bars, past, back=True)
    if not now or not then:
        return None
    idx_t = _num(now.get("idx"))
    idx_k = _num(then.get("idx"))
    if idx_t is None or idx_k is None:
        return None
    family = rule["family"]
    side: Optional[str] = None
    if family == "MOM":
        side = mom_side(idx_t=idx_t, idx_k=idx_k, thr=float(params["thr"]))
    elif family == "PDIV":
        atm = _num(now.get("atm"))
        if atm is None:
            return None
        side = pdiv_side(
            idx_t=idx_t,
            idx_k=idx_k,
            ce_t=strike_premium(now, "CE", atm) or 0.0,
            ce_k=strike_premium(then, "CE", atm) or 0.0,
            pe_t=strike_premium(now, "PE", atm) or 0.0,
            pe_k=strike_premium(then, "PE", atm) or 0.0,
            flat_thr=float(params["flat_thr"]),
            dv_thr=float(params["dv_thr"]),
        )
    if not side:
        return None
    if rule.get("vol_gate"):
        cut = VOL_CUT.get(str(underlying or "").upper())
        if not vol_gate_ok(rv30(bars, t), cut):
            return None
    return side


def _hhmm_ok(hhmm: str, start: tuple[int, int], end: tuple[int, int]) -> bool:
    hour, minute = (int(p) for p in hhmm.split(":"))
    stamp = hour * 60 + minute
    return start[0] * 60 + start[1] <= stamp <= end[0] * 60 + end[1]


def allowed(minutes: list[str], t: str) -> bool:
    if not _hhmm_ok(t, SIGNAL_START, SIGNAL_END):
        return False
    if not minutes:
        return False
    return t >= mplus(minutes[0], WARMUP_MIN)


def _bar_from_snap(snap: dict[str, Any], as_of: Any) -> Optional[dict[str, Any]]:
    idx = _num(snap.get("index_ltp"))
    ce = mid_or_ltp(snap.get("atm_ce_bid"), snap.get("atm_ce_ask"), snap.get("atm_ce_ltp"))
    pe = mid_or_ltp(snap.get("atm_pe_bid"), snap.get("atm_pe_ask"), snap.get("atm_pe_ltp"))
    atm = _num(snap.get("atm_strike"))
    ts = parse_ts(snap.get("as_of_ist") or as_of)
    if idx is None or ce is None or pe is None or atm is None or ts is None:
        return None
    when = datetime.fromtimestamp(int(ts), IST)
    return {
        "idx": idx,
        "ce": ce,
        "pe": pe,
        "atm": atm,
        "ts": int(ts),
        "hhmm": when.strftime("%H:%M"),
        "ist": when.isoformat(timespec="seconds"),
        "wings": snap.get("wing_quotes") if isinstance(snap.get("wing_quotes"), dict) else {},
    }


def _iter_tape_blobs(root: Path, day: str) -> Iterable[dict[str, Any]]:
    folder = dual_tape_dir(root)
    paths = [folder / f"{day}.jsonl", folder / "latest.json"]
    for path in paths:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if path.suffix == ".jsonl":
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    blob = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(blob, dict):
                    yield blob
        else:
            try:
                blob = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(blob, dict):
                yield blob


def load_atm_minutes(root: Path, underlying: str, day: str) -> dict[str, dict[str, Any]]:
    """Last dual-tape quote per IST minute. ATM CE/PE (mid if present, else LTP)."""
    und = underlying.upper()
    by_min: dict[str, dict[str, Any]] = {}
    seen: set[tuple[int, str]] = set()
    for blob in _iter_tape_blobs(root, day):
        as_of = blob.get("as_of_ist")
        for snap in blob.get("underlyings") or []:
            if not isinstance(snap, dict) or str(snap.get("underlying") or "").upper() != und:
                continue
            bar = _bar_from_snap(snap, as_of)
            if bar is None:
                continue
            key = (bar["ts"], bar["hhmm"])
            if key in seen:
                continue
            seen.add(key)
            by_min[bar["hhmm"]] = bar
    return dict(sorted(by_min.items()))


def _ist_ts(day: str, hhmm: str, bar: Optional[dict[str, Any]] = None) -> int:
    if bar is not None and bar.get("ts"):
        return int(bar["ts"])
    y, m, d = (int(p) for p in day.split("-"))
    hour, minute = (int(p) for p in hhmm.split(":"))
    return int(datetime(y, m, d, hour, minute, tzinfo=IST).timestamp())


def _ist_iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), IST).isoformat(timespec="seconds")


COST_MULT = 1.5  # spec PREREG_PRIMARY: 1.5x the #84 fixture


def _cost_row(*, entry: float, exit_px: float, qty: int, filled: bool) -> dict[str, Any]:
    raw = groww_round_trip_charges(
        exit_premium=float(exit_px),
        entry_premium=float(entry),
        qty=int(qty),
        filled=bool(filled),
    )
    out = dict(raw)
    for key, val in raw.items():
        if key.endswith("_inr") and isinstance(val, (int, float)):
            out[key] = round(float(val) * COST_MULT, 2)
    out["cost_mult"] = COST_MULT
    return out


def _trade_row(
    *,
    rule: dict[str, Any],
    underlying: str,
    side: str,
    strike: float,
    sig_min: str,
    entry_min: str,
    exit_min: str,
    entry: float,
    mark: float,
    day: str,
    entry_bar: dict[str, Any],
    mark_bar: Optional[dict[str, Any]],
    closed: bool,
    reason: Optional[str],
) -> dict[str, Any]:
    qty = int(QTY[underlying])
    lots = int(LOTS)
    lot_size = int(LOT_SIZE[underlying])
    opened_ts = _ist_ts(day, entry_min, entry_bar)
    closed_ts = _ist_ts(day, exit_min, mark_bar) if closed else None
    last_ts = closed_ts if closed else _ist_ts(day, mark_bar["hhmm"] if mark_bar else entry_min, mark_bar or entry_bar)
    charges = _cost_row(entry=entry, exit_px=mark, qty=qty, filled=True) if closed else None
    points = float(mark) - float(entry)
    gross = pnl_inr(points=points, lot_size=lot_size, lots=lots) if closed else None
    inr = net_pnl_inr(gross_inr=gross, charges_inr=float(charges["charges_inr"])) if closed and charges else None
    won = bool(inr is not None and inr > 0) if closed else None
    rule_id = str(rule["rule_id"])
    trade_id = f"RR-{rule_id}-{underlying}-{side}-{sig_min.replace(':', '')}"
    row: dict[str, Any] = {
        "book_id": rule_id,
        "rule_id": rule_id,
        "source_config": rule["source_config"],
        "model_names": [rule_id],
        "research_rule": True,
        "family": rule["family"],
        "underlying": underlying,
        "side": side,
        "trade_id": trade_id,
        "status": "CLOSED" if closed else "OPEN_PAPER",
        "phase": "FLAT" if closed else "IN_TRADE",
        "entry": round(float(entry), 4),
        "limit_price": round(float(entry), 4),
        "last_ltp": round(float(mark), 4),
        "exit": round(float(mark), 4) if closed else None,
        "stop": None,
        "target": None,
        "atm_strike": float(strike),
        "strike_source": "ATM_SIGNAL_MINUTE",
        "exit_reason": reason if closed else None,
        "sl_hit": False,
        "target_hit": False,
        "realized_pnl": round(points, 4) if closed else None,
        "gross_pnl_inr": gross,
        "charges_inr": charges["charges_inr"] if charges else None,
        "brokerage_inr": charges["brokerage_inr"] if charges else None,
        "gst_inr": charges["gst_inr"] if charges else None,
        "stt_inr": charges["stt_inr"] if charges else None,
        "exchange_inr": charges["exchange_inr"] if charges else None,
        "ipft_inr": charges["ipft_inr"] if charges else None,
        "sebi_inr": charges["sebi_inr"] if charges else None,
        "stamp_inr": charges["stamp_inr"] if charges else None,
        "realized_pnl_inr": inr,
        "lot_size": lot_size,
        "lots": lots,
        "qty": qty,
        "sig_min": sig_min,
        "entry_min": entry_min,
        "exit_min": exit_min,
        "opened_ts": opened_ts,
        "closed_ts": closed_ts,
        "last_updated_ts": last_ts,
        "opened_ist": _ist_iso(opened_ts),
        "closed_ist": _ist_iso(closed_ts) if closed_ts is not None else None,
        "last_updated_ist": _ist_iso(last_ts),
        "filled": True,
        "won": won,
        "result": ("SUCCESS" if won else "LOSS") if closed else None,
        "justification": f"{rule['source_config']} ATM paper fill. TIME exit. NO_PROMOTE.",
        "shadow": True,
        "execution": "refused",
        "orders": "REFUSED",
        "promote": False,
        "cost_fixture": "groww_round_trip_charges#84x1.5",
    }
    if charges:
        row["n_executed_orders"] = charges["n_executed_orders"]
        row["stt_status"] = charges["stt_status"]
    return row


def _premium_path(
    bars: dict[str, dict[str, Any]],
    *,
    side: str,
    strike: float,
    entry_min: str,
    exit_min: str,
) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for hhmm in bars:
        if hhmm < entry_min or hhmm > exit_min:
            continue
        px = strike_premium(bars[hhmm], side, strike)
        if px is not None:
            out.append((hhmm, float(px)))
    return out


def _with_exit_variants(
    row: dict[str, Any],
    bars: dict[str, dict[str, Any]],
    *,
    side: str,
    strike: float,
    entry: float,
    entry_min: str,
    exit_min: str,
    hold: int,
) -> dict[str, Any]:
    from desk_ml.shadow_exits import simulate_all

    path = _premium_path(bars, side=side, strike=strike, entry_min=entry_min, exit_min=exit_min)
    row["exit_variants"] = simulate_all(path, entry=entry, hold_min=hold)
    return row


GAP_TOL_MIN = 1        # D1: entry / look-back may use the nearest priced minute within 1 min
EXIT_TOL_MIN = 2       # D3: exit at the priced minute nearest the spec exit within +-2 min
LIVE_RULE_IDS = (R01, R01_B3A)   # D5: R02 PARKED -> shadow only
SHADOW_RULE_IDS = (R02,)
# R02 trades the desk already took before parking stay on the desk (history is never erased).
PARK_FROM_IST = {R02: {"2026-10-12": "11:50"}}  # other days: parked from the open


def _park_from(rule_id: str, day: str) -> Optional[str]:
    days = PARK_FROM_IST.get(rule_id)
    if days is None:
        return None
    return days.get(day, "00:00")


def _bar_near(bars: dict[str, dict[str, Any]], hhmm: str, *, back: bool, tol: int = GAP_TOL_MIN) -> Optional[dict[str, Any]]:
    for n in range(0, tol + 1):
        bar = bars.get(mplus(hhmm, -n if back else n))
        if bar is not None:
            return bar
    return None


def strike_quote(bar: dict[str, Any], side: str, strike: float, kind: str) -> tuple[Optional[float], Optional[str]]:
    """D2: ask for entries, bid for exits. Falls back to mid/LTP (flagged) only if the book side is missing."""
    cell = _wing_cell(bar.get("wings") or {}, strike)
    key = f"{side.lower()}_{kind}"
    px = _num(cell.get(key))
    if px is not None and px > 0:
        return px, None
    mid = strike_premium(bar, side, strike)
    return (mid, f"{kind.upper()}_MISSING_MID") if mid is not None else (None, None)


def _hm(x: str) -> int:
    return int(x[:2]) * 60 + int(x[3:])


def _pick_exit(bars, minutes, *, side, strike, spec_exit, entry_min, last_hhmm):
    """D3: exit at the spec minute if priced; else the priced minute nearest it within +-EXIT_TOL_MIN
    (tie -> earlier); else the last priced minute at/before it. Never later than spec+tol.
    Returns (minute, bid, flag) or None while undecided."""
    if last_hhmm < spec_exit:
        return None
    if spec_exit in bars:
        px, flag = strike_quote(bars[spec_exit], side, strike, "bid")
        if px is not None:
            return spec_exit, px, flag
    if last_hhmm < mplus(spec_exit, EXIT_TOL_MIN):
        return None  # a nearer minute inside the window may still arrive
    lo, hi = mplus(spec_exit, -EXIT_TOL_MIN), mplus(spec_exit, EXIT_TOL_MIN)
    cands = []
    for m in minutes:
        if entry_min < m and lo <= m <= hi:
            px, flag = strike_quote(bars[m], side, strike, "bid")
            if px is not None:
                cands.append((abs(_hm(m) - _hm(spec_exit)), m, px, flag))
    if cands:
        _, m, px, flag = min(cands)
        return m, px, ",".join(f for f in (flag, "EXIT_SHIFTED") if f)
    for m in reversed([m for m in minutes if entry_min < m <= spec_exit]):
        px, flag = strike_quote(bars[m], side, strike, "bid")
        if px is not None:
            return m, px, ",".join(f for f in (flag, "EXIT_EARLY_NO_QUOTE") if f)
    return None


def replay_underlying(
    bars: dict[str, dict[str, Any]],
    *,
    underlying: str,
    day: str,
    rules: Sequence[dict[str, Any]] = FROZEN_RULES,
    skip: Optional[set] = None,
    entry_before: Optional[dict[str, str]] = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    skip = skip or set()
    entry_before = entry_before or {}
    minutes = list(bars)
    opens: list[dict[str, Any]] = []
    closed: list[dict[str, Any]] = []
    last_hhmm = minutes[-1] if minutes else ""
    for rule in rules:
        busy = ""
        hold = int(rule["hold_min"])
        for t in minutes:
            if t <= busy or not allowed(minutes, t):
                continue
            side = signal(rule, bars, t, underlying=underlying)
            if not side:
                continue
            if entry_before.get(rule["rule_id"]) is not None and mplus(t, 1) >= entry_before[rule["rule_id"]]:
                continue  # parked from here on: not a desk trade
            if (rule["rule_id"], underlying, t) in skip:
                continue  # D6: guard-blocked signal -> not traded, rule not busy
            atm = _num(bars[t].get("atm"))
            if atm is None:
                continue
            entry_bar = _bar_near(bars, mplus(t, 1), back=False)
            if entry_bar is None:
                continue
            entry_min = entry_bar["hhmm"]
            entry, entry_flag = strike_quote(entry_bar, side, atm, "ask")
            if entry is None:
                continue
            spec_exit = mplus(entry_min, hold)
            pick = _pick_exit(bars, minutes, side=side, strike=atm, spec_exit=spec_exit,
                              entry_min=entry_min, last_hhmm=last_hhmm)
            flags = [f for f in (entry_flag,) if f]
            if pick is not None:
                exit_min, mark, exit_flag = pick
                if exit_flag:
                    flags.append(exit_flag)
                mark_bar = bars[exit_min]
                row = _trade_row(rule=rule, underlying=underlying, side=side, strike=atm, sig_min=t,
                                 entry_min=entry_min, exit_min=exit_min, entry=entry, mark=mark, day=day,
                                 entry_bar=entry_bar, mark_bar=mark_bar, closed=True, reason="TIME")
                row["spec_exit_min"] = spec_exit
                row["price_flags"] = flags
                closed.append(_with_exit_variants(row, bars, side=side, strike=atm, entry=entry,
                                                  entry_min=entry_min, exit_min=exit_min, hold=hold))
                busy = max(exit_min, spec_exit)
            elif last_hhmm >= entry_min:
                mark_bar = bars.get(last_hhmm)
                mark = strike_quote(mark_bar, side, atm, "bid")[0] if mark_bar else None
                if mark is None:
                    mark = entry
                row = _trade_row(rule=rule, underlying=underlying, side=side, strike=atm, sig_min=t,
                                 entry_min=entry_min, exit_min=spec_exit, entry=entry, mark=mark, day=day,
                                 entry_bar=entry_bar, mark_bar=mark_bar, closed=False, reason=None)
                row["spec_exit_min"] = spec_exit
                row["price_flags"] = flags
                opens.append(_with_exit_variants(row, bars, side=side, strike=atm, entry=entry,
                                                 entry_min=entry_min, exit_min=min(spec_exit, last_hhmm), hold=hold))
                busy = mplus(spec_exit, EXIT_TOL_MIN)
    return opens, closed


# Guard go-live per IST day (HH:MM). Trades entered before it are history and are never erased.
# Days not listed: guard applies from the open. Override with DESK_GUARD_FROM_IST="YYYY-MM-DD HH:MM" or "HH:MM".
GUARD_FROM_IST = {"2026-10-12": "11:19"}


def guard_from(day: str) -> str:
    raw = os.environ.get("DESK_GUARD_FROM_IST", "").strip()
    if raw:
        parts = raw.split()
        if len(parts) == 2 and parts[0] == day:
            return parts[1]
        if len(parts) == 1:
            return parts[0]
    return GUARD_FROM_IST.get(day, "00:00")


def _same_direction_guard(opens, closed, day: str = ""):
    """Never hold NIFTY and SENSEX on opposite sides at once (earlier entry wins). Trades entered before
    the guard went live are kept with real P&L. Blocked trades are listed, not traded."""
    rows = [(r, True) for r in opens] + [(r, False) for r in closed]
    rows.sort(key=lambda x: (str(x[0].get("entry_min") or ""), str(x[0].get("sig_min") or "")))
    kept = []
    blocked = []
    for r, is_open in rows:
        t = str(r.get("entry_min") or "")
        if t < guard_from(day or str(r.get("day") or "")):
            kept.append((r, is_open))
            continue
        clash = False
        for k, k_open in kept:
            if k.get("underlying") == r.get("underlying") or k.get("side") == r.get("side"):
                continue
            ks = str(k.get("entry_min") or "")
            ke = "99:99" if k_open else str(k.get("exit_min") or "99:99")
            if ks <= t < ke:
                clash = True
                break
        if clash:
            b = dict(r); b["guard"] = "BLOCKED_OPPOSITE_SIDE"; blocked.append(b)
        else:
            kept.append((r, is_open))
    return [r for r, o in kept if o], [r for r, o in kept if not o], blocked


def replay(
    root: Path,
    day: str,
    *,
    underlyings: Iterable[str] = UNDERLYINGS,
    rules: Optional[Sequence[dict[str, Any]]] = None,
) -> dict[str, Any]:
    live_rules = [r for r in FROZEN_RULES if r["rule_id"] in LIVE_RULE_IDS] if rules is None else list(rules)
    entry_before: dict[str, str] = {}
    if rules is None:
        for r in FROZEN_RULES:
            pf = _park_from(r["rule_id"], day)
            if r["rule_id"] in SHADOW_RULE_IDS and pf and pf > "00:00":
                live_rules.append(r)  # pre-park history only
                entry_before[r["rule_id"]] = pf
    shadow_rules = [r for r in FROZEN_RULES if r["rule_id"] in SHADOW_RULE_IDS] if rules is None else []
    bars_by = {und: load_atm_minutes(Path(root), und, day) for und in underlyings}
    skip: set = set()
    blocked: list[dict[str, Any]] = []
    for _ in range(10):  # D6: re-run without blocked signals until the blocked set is stable
        opens, closed = [], []
        for und, bars in bars_by.items():
            o, c = replay_underlying(bars, underlying=und, day=day, rules=live_rules, skip=skip,
                                    entry_before=entry_before)
            opens.extend(o); closed.extend(c)
        opens, closed, new_blocked = _same_direction_guard(opens, closed, day)
        blocked.extend(new_blocked)
        add = {(b["rule_id"], b["underlying"], b["sig_min"]) for b in new_blocked}
        if not add - skip:
            break
        skip |= add
    shadow_open, shadow_closed = [], []
    for und, bars in bars_by.items():
        o, c = replay_underlying(bars, underlying=und, day=day, rules=shadow_rules)
        shadow_open.extend(o); shadow_closed.extend(c)
    per = {und: {"n_minutes": len(bars_by[und]),
                 "n_open": sum(1 for r in opens if r["underlying"] == und),
                 "n_closed": sum(1 for r in closed if r["underlying"] == und)} for und in bars_by}
    uniq = {}
    for b in blocked:
        uniq[(b["rule_id"], b["underlying"], b["sig_min"])] = b
    return {
        "guard_blocked": list(uniq.values()),
        "shadow_parked": {"rule_ids": [r["rule_id"] for r in shadow_rules], "open": shadow_open,
                          "closed": shadow_closed, "note": "PARKED rules: computed, not traded, not in desk P&L"},
        "enabled": True,
        "flag": FLAG_ENV,
        "rule_ids": [r["rule_id"] for r in live_rules],
        "underlyings": list(underlyings),
        "qty": dict(QTY),
        "lots": LOTS,
        "pricing": "ask-in / bid-out (mid fallback flagged), costs 1.5x #84",
        "open": opens,
        "closed": closed,
        "per_underlying": per,
        "execution": "refused",
        "orders": "REFUSED",
        "promote": False,
    }


def _strip_research(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not row.get("research_rule")]


def attach_to_board(
    board: dict[str, Any],
    *,
    root: Optional[Path] = None,
    environ: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Merge frozen-rule paper tickets onto the desk board. Never a broker."""
    out = dict(board)
    if not enabled(environ):
        out["research_rules"] = {"enabled": False, "flag": FLAG_ENV, "orders": "REFUSED"}
        return out
    base = Path(root) if root is not None else repo_root()
    day = str(out.get("session_ist_date") or datetime.now(IST).date().isoformat())
    try:
        result = replay(base, day)
    except Exception as exc:  # noqa: BLE001 — SOD board must still publish
        out["research_rules"] = {
            "enabled": True,
            "flag": FLAG_ENV,
            "error": f"{type(exc).__name__}: {exc}"[:240],
            "orders": "REFUSED",
        }
        return out
    opens = result["open"] + _strip_research(out.get("open_trades") or [])
    closed = result["closed"] + _strip_research(out.get("closed_trades") or [])
    out["open_trades"] = opens
    out["closed_trades"] = closed
    out["tickets"] = list(opens) + list(closed)
    out["n_open"] = len(opens)
    out["research_rules"] = {
        "enabled": True,
        "flag": FLAG_ENV,
        "rule_ids": result["rule_ids"],
        "n_open": len(result["open"]),
        "n_closed": len(result["closed"]),
        "qty": result["qty"],
        "per_underlying": result["per_underlying"],
        "execution": "refused",
        "orders": "REFUSED",
        "promote": False,
        "cost_fixture": "groww_round_trip_charges#84x1.5",
    }
    try:
        journal = base / "data" / "recon" / "research_rules" / f"{day}.json"
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    except OSError:
        pass
    try:
        from desk_ml.shadow_exits import attach_and_log

        attach_and_log(result.get("closed") or [], root=base, environ=environ)
    except Exception:  # noqa: BLE001 — shadow log must not block the board
        pass
    return out


def publish_board(board: dict[str, Any], *, root: Path) -> None:
    from desk_ml.paper_scalp import write_dashboard

    write_dashboard(board, root=root)
