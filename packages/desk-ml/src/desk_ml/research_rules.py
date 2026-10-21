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
    from desk_ml.tape import is_carried_over

    if is_carried_over(snap):
        return None  # carried-over / filler print (e.g. 2026-10-12 10:31-11:02 NIFTY): never a fresh bar
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


V2_TAPE_DIR = ("data", "tape", "v2")
V2_INDEX_ID = {"NIFTY": "NSE_IDX:NIFTY", "SENSEX": "BSE_IDX:SENSEX"}
V2_FNO_PREFIX = {"NIFTY": "NSE_FNO:NIFTY:", "SENSEX": "BSE_FNO:SENSEX:"}


def _v2_lines(path: Path, needle: bytes, start: int = 0, stats: Optional[dict] = None) -> Iterable[dict[str, Any]]:
    """Stream a V2 recorder jsonl from byte `start`, decoding only lines that contain `needle` (files run to
    ~2 GB). Stops at the last complete line; `stats["end"]` = offset after it (for incremental reads)."""
    if stats is not None:
        stats["end"] = start
    if not path.is_file():
        return
    with path.open("rb") as fh:
        fh.seek(start)
        pos = start
        for raw in fh:
            if not raw.endswith(b"\n"):
                break  # recorder mid-write: read it next time
            pos += len(raw)
            if stats is not None:
                stats["end"] = pos
            if not any(n in raw for n in (needle if isinstance(needle, tuple) else (needle,))):
                continue
            try:
                blob = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(blob, dict) and isinstance(blob.get("payload"), dict):
                yield blob


# Incremental V2 state per (root, underlying, day): live calls read only the bytes appended since the
# last call, so V2-primary pricing does not rescan ~2 GB every loop cycle (that would add lag).
_V2_STATE: dict[tuple[str, str, str], dict[str, Any]] = {}


def load_v2_minutes(root: Path, underlying: str, day: str) -> dict[str, dict[str, Any]]:
    """Minute bars from the V2 recorder (data/tape/v2/<day>/): index = last NSE/BSE_IDX print of the
    minute (depth_quotes); option quotes = last non-null QUOTE_SNAPSHOT per strike/side of the minute
    (bid/ask/ltp). ATM = the snapshot rule ATM strike. Same bar shape as load_atm_minutes, plus
    source="v2". Read-only. Incremental across calls (files only grow)."""
    und = underlying.upper()
    folder = Path(root).joinpath(*V2_TAPE_DIR, day)
    key = (str(Path(root).resolve()), und, day)
    st = _V2_STATE.get(key)
    dq, qs = folder / "depth_quotes.jsonl", folder / "quote_snapshots.jsonl"
    sizes = (dq.stat().st_size if dq.is_file() else 0, qs.stat().st_size if qs.is_file() else 0)
    if st is None or sizes[0] < st["off_dq"] or sizes[1] < st["off_qs"]:  # new or truncated: start over
        st = {"off_dq": 0, "off_qs": 0, "idx": {}, "quotes": {}, "atm": {}, "ts": {}}
        _V2_STATE[key] = st
    idx_by_min, quotes, atm_by_min, ts_by_min = st["idx"], st["quotes"], st["atm"], st["ts"]
    stats: dict = {}
    depth = st.setdefault("depth", {})  # hhmm -> strike -> side -> (ts, bid_levels, ask_levels)
    fno = V2_FNO_PREFIX[und]
    for blob in _v2_lines(dq, (V2_INDEX_ID[und].encode(), fno.encode()), st["off_dq"], stats):
        pay = blob["payload"]
        iid = str(pay.get("instrument_id") or "")
        if iid.startswith(fno):  # option book levels for depth-walk fills (fix 8)
            lv = pay.get("levels") if isinstance(pay.get("levels"), dict) else {}
            parts = iid.split(":")
            if len(parts) >= 5 and (lv.get("bid") or lv.get("ask")):
                try:
                    k_strike, k_side = float(parts[3]), parts[4].lower()
                except ValueError:
                    continue
                dts = parse_ts(pay.get("exchange_ts") or blob.get("timestamp"))
                if dts is None:
                    continue
                dm = datetime.fromtimestamp(dts, IST).strftime("%H:%M")
                cur = depth.setdefault(dm, {}).setdefault(k_strike, {}).get(k_side)
                if cur is None or dts >= cur[0]:
                    depth[dm][k_strike][k_side] = (dts, lv.get("bid") or [], lv.get("ask") or [])
            continue
        if iid != V2_INDEX_ID[und]:
            continue
        ltp = _num(pay.get("ltp"))
        ts = parse_ts(pay.get("exchange_ts") or blob.get("timestamp"))
        if ltp is None or ts is None:
            continue
        hhmm = datetime.fromtimestamp(ts, IST).strftime("%H:%M")
        if hhmm not in idx_by_min or ts >= idx_by_min[hhmm][0]:
            idx_by_min[hhmm] = (ts, ltp)
    st["off_dq"] = stats.get("end", st["off_dq"])
    prefix = V2_FNO_PREFIX[und]
    stats = {}
    for blob in _v2_lines(qs, prefix.encode(), st["off_qs"], stats):
        pay = blob["payload"]
        iid = str(pay.get("instrument_id") or "")
        if not iid.startswith(prefix):
            continue
        parts = iid.split(":")
        try:
            strike = float(parts[3])
            side = parts[4].upper()
        except (IndexError, ValueError):
            continue
        bid, ask, ltp = _num(pay.get("bid")), _num(pay.get("ask")), _num(pay.get("ltp"))
        if bid is None and ask is None and ltp is None:
            continue
        ts = parse_ts(blob.get("timestamp"))
        if ts is None:
            continue
        hhmm = datetime.fromtimestamp(ts, IST).strftime("%H:%M")
        cell = quotes.setdefault(hhmm, {}).setdefault(strike, {})
        k = side.lower()
        cell[k] = mid_or_ltp(bid, ask, ltp)
        cell[f"{k}_bid"] = bid
        cell[f"{k}_ask"] = ask
        cell[f"{k}_ltp"] = ltp
        if pay.get("rule") == "ATM":
            atm_by_min[hhmm] = strike
        ts_by_min[hhmm] = max(ts, ts_by_min.get(hhmm, 0))
    st["off_qs"] = stats.get("end", st["off_qs"])
    out: dict[str, dict[str, Any]] = {}
    for hhmm in sorted(quotes):
        atm = atm_by_min.get(hhmm)
        idx = idx_by_min.get(hhmm)
        if atm is None or idx is None:
            continue
        cell = quotes[hhmm].get(atm) or {}
        if cell.get("ce") is None or cell.get("pe") is None:
            continue
        wings = {(str(int(k)) if k == int(k) else str(k)): dict(v) for k, v in quotes[hhmm].items()}
        for k_strike, sides in (depth.get(hhmm) or {}).items():
            cell_w = wings.setdefault(str(int(k_strike)) if k_strike == int(k_strike) else str(k_strike), {})
            for k_side, (_dts, bids, asks) in sides.items():
                cell_w[f"{k_side}_bid_levels"] = bids
                cell_w[f"{k_side}_ask_levels"] = asks
        ts = ts_by_min[hhmm]
        out[hhmm] = {"idx": idx[1], "ce": cell["ce"], "pe": cell["pe"], "atm": atm, "ts": int(ts),
                     "hhmm": hhmm, "ist": datetime.fromtimestamp(ts, IST).isoformat(timespec="seconds"),
                     "wings": wings, "source": "v2"}
    return out


def load_minutes_v2_primary(root: Path, underlying: str, day: str) -> dict[str, dict[str, Any]]:
    """2026-10-12: V2 recorder is the PRIMARY price/signal source; the legacy DUAL-TAPE only fills minutes
    V2 lacks (bar["source"] == "dual_tape_fallback"). Carried-over legacy snaps are already dropped."""
    bars = {m: dict(b) for m, b in load_v2_minutes(root, underlying, day).items()}
    for hhmm, bar in load_atm_minutes(root, underlying, day).items():
        if hhmm not in bars:
            bars[hhmm] = {**bar, "source": "dual_tape_fallback"}
    return dict(sorted(bars.items()))


def load_minutes_filled(root: Path, underlying: str, day: str) -> dict[str, dict[str, Any]]:
    """DUAL-TAPE minutes first; every minute the dual-tape jsonl lacks is filled from the V2 recorder
    (bar["source"] == "v2_fill"). Dual-tape bars are never overwritten."""
    bars = load_atm_minutes(root, underlying, day)
    for hhmm, bar in bars.items():
        bar.setdefault("source", "dual_tape")
    for hhmm, bar in load_v2_minutes(root, underlying, day).items():
        if hhmm not in bars:
            bars[hhmm] = {**bar, "source": "v2_fill"}
    return dict(sorted(bars.items()))


def _ist_ts(day: str, hhmm: str, bar: Optional[dict[str, Any]] = None) -> int:
    if bar is not None and bar.get("ts"):
        return int(bar["ts"])
    y, m, d = (int(p) for p in day.split("-"))
    hour, minute = (int(p) for p in hhmm.split(":"))
    return int(datetime(y, m, d, hour, minute, tzinfo=IST).timestamp())


def _ist_iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), IST).isoformat(timespec="seconds")


COST_MULT = 1.5  # spec PREREG_PRIMARY: 1.5x the #84 fixture


def _cost_row(*, entry: float, exit_px: float, qty: int, filled: bool, underlying: Optional[str] = None) -> dict[str, Any]:
    raw = groww_round_trip_charges(
        underlying=underlying,
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


TRADED = "TRADED"
SHADOW_PARKED = "SHADOW_PARKED"
BLOCKED_OPPOSITE_SIDE = "BLOCKED_OPPOSITE_SIDE"
DESK_STATUSES = (TRADED, SHADOW_PARKED, BLOCKED_OPPOSITE_SIDE, "DUP_SAME_CONTRACT",
                 "RISK_CAP_TRADES", "RISK_CAP_OPEN", "RISK_DAY_STOP")


def _mark(rows, status: str, *, shadow: bool):
    for r in rows:
        r["desk_status"] = status
        r["shadow"] = shadow
    return rows


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
    charges = _cost_row(entry=entry, exit_px=mark, qty=qty, filled=True, underlying=underlying) if closed else None
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
        "held_strike": float(strike),
        "entry_price_source": str(entry_bar.get("source") or "dual_tape"),
        "exit_price_source": (str(mark_bar.get("source") or "dual_tape") if mark_bar else None),
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
        "shadow": False,  # desk trade; shadow lists set True (see _mark)
        "desk_status": TRADED,
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


DESK_RULES_OFF_PATH = Path(__file__).resolve().parents[4] / "config" / "desk_rules_off.yaml"


def desk_rules_off(path: Optional[Path] = None) -> set[str]:
    """Rule ids switched off from desk slots/promotion (config/desk_rules_off.yaml). Shadow scoring keeps them."""
    p = Path(path) if path is not None else DESK_RULES_OFF_PATH
    if not p.is_file():
        return set()
    import yaml

    blob = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    out: set[str] = set()
    for item in blob.get("rules_off") or []:
        out.add(str(item.get("id")))
        out.update(str(m) for m in item.get("match") or [])
    return out


def desk_shadow_only(day: str, path: Optional[Path] = None) -> set[str]:
    """Rule ids that are SHADOW ONLY on `day` (config/desk_rules_off.yaml `shadow_only`, each with an IST `from` day).
    They keep generating signals and are scored as shadow, but book nothing and use no slot / premium cap."""
    p = Path(path) if path is not None else DESK_RULES_OFF_PATH
    if not p.is_file():
        return set()
    import yaml

    blob = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    out: set[str] = set()
    for item in blob.get("shadow_only") or []:
        if str(day) >= str(item.get("from") or "9999-99-99"):
            out.add(str(item.get("id")))
            out.update(str(m) for m in item.get("match") or [])
    return out


def split_shadow_only(rows, ids: set):
    """(desk rows, shadow rows) for the shadow_only list."""
    keep, sh = [], []
    for r in rows:
        if str(r.get("rule_id") or "") in ids:
            r["shadow_reason"] = "SHADOW_ONLY (config/desk_rules_off.yaml shadow_only)"
            sh.append(r)
        else:
            keep.append(r)
    return keep, sh


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


def walk_book(levels: Any, qty: int) -> tuple[Optional[float], Optional[str]]:
    """2026-10-12 fix 8: average fill price for `qty` walking recorded book levels [[price, qty], ...] in
    the order given (best first). Depth short of qty: the rest fills at the last level, flagged DEPTH_SHORT.
    Returns (vwap, flag); flag DEPTH_WALK when more than the top level was used."""
    rows = []
    for lv in levels or []:
        try:
            px, q = float(lv[0]), int(lv[1])
        except (TypeError, ValueError, IndexError):
            continue
        if px > 0 and q > 0:
            rows.append((px, q))
    if not rows or qty <= 0:
        return None, None
    left, cost, used = int(qty), 0.0, 0
    for px, q in rows:
        take = min(left, q)
        cost += take * px
        left -= take
        used += 1
        if left == 0:
            break
    flag = None
    if left > 0:
        cost += left * rows[-1][0]
        flag = "DEPTH_SHORT"
    elif used > 1:
        flag = "DEPTH_WALK"
    return round(cost / qty, 4), flag


def strike_quote(bar: dict[str, Any], side: str, strike: float, kind: str,
                 qty: Optional[int] = None) -> tuple[Optional[float], Optional[str]]:
    """D2: ask for entries, bid for exits. With `qty` and recorded levels (V2 depth), the fill walks the
    book for the order qty (fix 8). Falls back to mid/LTP (flagged) only if the book side is missing."""
    cell = _wing_cell(bar.get("wings") or {}, strike)
    if qty:
        lv_px, lv_flag = walk_book(cell.get(f"{side.lower()}_{kind}_levels"), int(qty))
        if lv_px is not None:
            return lv_px, lv_flag
    key = f"{side.lower()}_{kind}"
    px = _num(cell.get(key))
    if px is not None and px > 0:
        return px, None
    mid = strike_premium(bar, side, strike)
    return (mid, f"{kind.upper()}_MISSING_MID") if mid is not None else (None, None)


def _hm(x: str) -> int:
    return int(x[:2]) * 60 + int(x[3:])


# Sahil 2026-10-14 22:19 CT: no time exits. Fixed premium stop and target on the held option's bid;
# only the 15:14 IST safety close remains. Stop checked before target in the same minute.
PRICE_EXITS = True
PREMIUM_STOP_PCT = 0.30
PREMIUM_TARGET_PCT = 0.60
EOD_EXIT = "15:14"


def _price_exit(bars, minutes, *, side, strike, entry, entry_min, spec_exit, qty=None):
    stop, tgt = entry * (1 - PREMIUM_STOP_PCT), entry * (1 + PREMIUM_TARGET_PCT)
    for m in minutes:
        if m <= entry_min or m > spec_exit:
            continue
        px, flag = strike_quote(bars[m], side, strike, "bid", qty=qty)
        if px is None:
            continue
        if px <= stop:
            return m, px, ",".join(f for f in (flag, "STOP") if f)
        if px >= tgt:
            return m, px, ",".join(f for f in (flag, "TARGET") if f)
    return None


def _pick_exit(bars, minutes, *, side, strike, spec_exit, entry_min, last_hhmm, now_hhmm=None, qty=None):
    """D3: exit at the spec minute if priced; else the priced minute nearest it within +-EXIT_TOL_MIN
    (tie -> earlier); else the last priced minute at/before it. Never later than spec+tol.
    Decided as soon as the tape has a minute past the exit (no later minute can be nearer) or the
    wall clock (`now_hhmm`, live only) reaches the exit. Returns (minute, bid, flag) or None."""
    clock = max(last_hhmm, now_hhmm) if now_hhmm else last_hhmm
    if clock < spec_exit:
        return None
    if spec_exit in bars:
        px, flag = strike_quote(bars[spec_exit], side, strike, "bid", qty=qty)
        if px is not None:
            return spec_exit, px, flag
    # 2026-10-12 fix: the old rule waited for the tape to reach spec+2. The DUAL-TAPE writes every
    # ~1-3 min and can stall, so H20 trades sat OPEN past their exit (R01 NIFTY 11:57 -> 12:19).
    lo, hi = mplus(spec_exit, -EXIT_TOL_MIN), mplus(spec_exit, EXIT_TOL_MIN)
    cands = []
    for m in minutes:
        if entry_min < m and lo <= m <= hi:
            px, flag = strike_quote(bars[m], side, strike, "bid", qty=qty)
            if px is not None:
                cands.append((abs(_hm(m) - _hm(spec_exit)), m, px, flag))
    if cands:
        _, m, px, flag = min(cands)
        return m, px, ",".join(f for f in (flag, "EXIT_SHIFTED") if f)
    for m in reversed([m for m in minutes if entry_min < m <= spec_exit]):
        px, flag = strike_quote(bars[m], side, strike, "bid", qty=qty)
        if px is not None:
            return m, px, ",".join(f for f in (flag, "EXIT_EARLY_NO_QUOTE") if f)
    # no quote for the held strike anywhere in (entry, spec]: first priced minute after it, else
    # the entry price itself (flat, flagged). Never left open.
    for m in [m for m in minutes if m > spec_exit]:
        px, flag = strike_quote(bars[m], side, strike, "bid", qty=qty)
        if px is not None:
            return m, px, ",".join(f for f in (flag, "EXIT_LATE_NO_QUOTE") if f)
    return entry_min, None, "EXIT_NO_QUOTE_AT_ENTRY_PX"


def replay_underlying(
    bars: dict[str, dict[str, Any]],
    *,
    underlying: str,
    day: str,
    rules: Sequence[dict[str, Any]] = FROZEN_RULES,
    skip: Optional[set] = None,
    entry_before: Optional[dict[str, str]] = None,
    now_hhmm: Optional[str] = None,
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
            entry, entry_flag = strike_quote(entry_bar, side, atm, "ask", qty=QTY.get(underlying.upper()))
            if entry is None:
                continue
            spec_exit = EOD_EXIT if PRICE_EXITS else mplus(entry_min, hold)
            pick = _price_exit(bars, minutes, side=side, strike=atm, entry=entry, entry_min=entry_min,
                               spec_exit=spec_exit, qty=QTY.get(underlying.upper())) if PRICE_EXITS else None
            if pick is None:
                pick = _pick_exit(bars, minutes, side=side, strike=atm, spec_exit=spec_exit,
                              entry_min=entry_min, last_hhmm=last_hhmm, now_hhmm=now_hhmm,
                              qty=QTY.get(underlying.upper()))
            flags = [f for f in (entry_flag,) if f]
            if pick is not None:
                exit_min, mark, exit_flag = pick
                if mark is None:
                    mark = entry
                if exit_flag:
                    flags.append(exit_flag)
                mark_bar = bars[exit_min]
                row = _trade_row(rule=rule, underlying=underlying, side=side, strike=atm, sig_min=t,
                                 entry_min=entry_min, exit_min=exit_min, entry=entry, mark=mark, day=day,
                                 entry_bar=entry_bar, mark_bar=mark_bar, closed=True,
                                 reason=(exit_flag or "").split(",")[-1] if (exit_flag or "").endswith(("STOP", "TARGET")) else ("FLATTEN_EOD" if PRICE_EXITS else "TIME"))
                row["spec_exit_min"] = spec_exit
                row["price_flags"] = flags
                closed.append(_with_exit_variants(row, bars, side=side, strike=atm, entry=entry,
                                                  entry_min=entry_min, exit_min=exit_min, hold=hold))
                busy = max(exit_min, spec_exit)
            elif last_hhmm >= entry_min:
                mark_bar = bars.get(last_hhmm)
                mark = strike_quote(mark_bar, side, atm, "bid", qty=QTY.get(underlying.upper()))[0] if mark_bar else None
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


def _holds_at(k: dict[str, Any], k_open: bool, t: str) -> bool:
    """True if desk position `k` is (or may still be) held at minute `t`: from its entry through
    max(exit_min, spec_exit_min) inclusive; open (or overdue) positions hold until closed."""
    ks = str(k.get("entry_min") or "")
    if k_open:
        return ks <= t
    ke = max(str(k.get("exit_min") or "99:99"), str(k.get("spec_exit_min") or ""))
    return ks <= t <= ke


def _same_direction_guard(opens, closed, day: str = ""):
    """Never hold CE and PE at once on any index (NIFTY+SENSEX, or both sides of one index); earlier entry wins. Trades entered before
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
            # 2026-10-12 fix: same index counts too (CE and PE on NIFTY at once was allowed), and a
            # position is held through max(booked exit, spec exit) inclusive: an EXIT_SHIFTED exit can
            # be booked at a minute earlier than when the exit was actually decided live.
            if k.get("side") == r.get("side"):
                continue
            if _holds_at(k, k_open, t):
                clash = True
                break
        if clash:
            b = dict(r); b["guard"] = "BLOCKED_OPPOSITE_SIDE"; blocked.append(b)
        else:
            kept.append((r, is_open))
    return [r for r, o in kept if o], [r for r, o in kept if not o], blocked


DUP_SAME_CONTRACT = "DUP_SAME_CONTRACT"


def _dedupe_same_contract(opens, closed, rule_order):
    """One desk position per contract (underlying, side, held strike) per entry minute across rule
    slots. The first slot in `rule_order` keeps it; the others are tagged DUP_SAME_CONTRACT and
    returned as shadow (computed, not traded, not in desk P&L)."""
    rank = {rid: i for i, rid in enumerate(rule_order)}
    rows = [(r, True) for r in opens] + [(r, False) for r in closed]
    rows.sort(key=lambda x: (rank.get(x[0]["rule_id"], 99), x[0]["rule_id"]))
    owner: dict = {}
    keep_o, keep_c, dups = [], [], []
    for r, is_open in rows:
        key = (r["underlying"], r["side"], float(r["atm_strike"]), r["entry_min"])
        if key in owner:
            d = dict(r); d["dup_of"] = owner[key]; d["guard"] = DUP_SAME_CONTRACT
            dups.append(d)
            continue
        owner[key] = r["trade_id"]
        (keep_o if is_open else keep_c).append(r)
    return keep_o, keep_c, dups


Q01_RULE_ID = "Q01_ITM100"
Q01_FROM_DAY = "2026-10-14"
Q01_WINDOW = ("09:55", "10:21")
BLOCKED_Q01_WINDOW = "BLOCKED_Q01_WINDOW"
Q01_SKIPPED_CAP = "Q01_SKIPPED_CAP"


def q01_priority_window(root: Path, day: str) -> Optional[tuple]:
    """2026-10-13 Sahil: Q01 has priority. On Q01 days, no other NIFTY entry 09:55-10:21 IST. Armed state comes from the
    paper_extra runner (pre-open VIX filter); unknown -> block anyway (fail safe). Known NOT armed -> no window."""
    if day < Q01_FROM_DAY:
        return None
    try:
        blob = json.loads((Path(root) / PAPER_EXTRA_REL / f"{day}.json").read_text(encoding="utf-8"))
        armed = (blob.get("q01") or {}).get("armed") if blob.get("day") == day else None
    except (OSError, ValueError):
        armed = None
    return None if armed is False else Q01_WINDOW


def _desk_pass(opens, closed, day: str, rule_order, risk_cfg, q01_window: Optional[tuple] = None):
    """One pass over desk candidates in strict entry-minute order (then rule rank):
    1) opposite-side guard (any index), 2) same-contract dedup, 3) desk risk gate (desk_risk.py).
    Trades entered before guard_from(day) are history: kept, but they count in the gate's state.
    Returns opens, closed, blocked (guard+risk, rule not busy), dups, taken[(row, is_open)]."""
    from desk_ml import desk_risk

    rank = {rid: i for i, rid in enumerate(rule_order)}
    rows = [(r, True) for r in opens] + [(r, False) for r in closed]
    rows.sort(key=lambda x: (str(x[0].get("entry_min") or ""), rank.get(x[0].get("rule_id"), 99),
                             str(x[0].get("sig_min") or "")))
    taken: list = []
    blocked: list = []
    dups: list = []
    owner: dict = {}
    for r, is_open in rows:
        t = str(r.get("entry_min") or "")
        pre = t < guard_from(day or str(r.get("day") or ""))
        # Q01 priority: other NIFTY entries inside the window are blocked (open positions are never force-closed).
        if (q01_window and str(r.get("underlying") or "").upper() == "NIFTY" and r.get("rule_id") != Q01_RULE_ID
                and q01_window[0] <= t <= q01_window[1]):
            b = dict(r); b["guard"] = BLOCKED_Q01_WINDOW; blocked.append(b)
            continue
        key = (r.get("underlying"), r.get("side"), float(r.get("atm_strike") or 0), t)
        if not pre and any(k.get("side") != r.get("side") and _holds_at(k, k_open, t) for k, k_open in taken):
            b = dict(r); b["guard"] = BLOCKED_OPPOSITE_SIDE; blocked.append(b)
            continue
        # 2026-10-12 fix: same contract already HELD (not only same entry minute) is a repeat buy.
        # Live 12:33/12:38 IST: R01_PDIV and R01_B3A both bought NIFTY 22400 CE while one was open.
        held = next((k for k, k_open in taken
                     if (k.get("underlying"), k.get("side"), float(k.get("atm_strike") or 0)) == key[:3]
                     and _holds_at(k, k_open, t)), None)
        if key in owner or held is not None:
            d = dict(r); d["dup_of"] = owner.get(key) or held.get("trade_id"); d["guard"] = DUP_SAME_CONTRACT
            dups.append(d)
            continue
        # 2026-10-12: hard 10-lot cap on TOTAL open qty per underlying across rules (NIFTY 650, SENSEX 200).
        und = str(r.get("underlying") or "").upper()
        held_qty = sum(int(k.get("qty") or QTY.get(und, 0)) for k, k_open in taken
                       if str(k.get("underlying") or "").upper() == und and _holds_at(k, k_open, t))
        if held_qty + int(r.get("qty") or QTY.get(und, 0)) > QTY.get(und, 10**9):
            b = dict(r); b["guard"] = Q01_SKIPPED_CAP if r.get("rule_id") == Q01_RULE_ID else desk_risk.RISK_CAP_QTY; blocked.append(b)
            continue
        if not pre:
            why = desk_risk.check(taken, r, risk_cfg)
            if why:
                b = dict(r); b["guard"] = why; blocked.append(b)
                continue
        owner[key] = r.get("trade_id")
        taken.append((r, is_open))
    return [r for r, o in taken if o], [r for r, o in taken if not o], blocked, dups, taken



# ---- 2026-10-13: mid-day switch-on + paper_extra (lab strategies run by scripts/paper_extra) ----
DESK_RULES_ON_FROM_PATH = Path(__file__).resolve().parents[4] / "config" / "desk_rules_on_from.yaml"
PAPER_EXTRA_REL = Path("data") / "recon" / "paper_extra"


def rules_on_from(day: str, path: Optional[Path] = None) -> dict[str, str]:
    """{rule_id or prefix*: 'HH:MM'} for `day`: desk trades only from that IST minute; earlier = shadow."""
    p = Path(path) if path is not None else DESK_RULES_ON_FROM_PATH
    if not p.is_file():
        return {}
    import yaml

    blob = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in ((blob.get("on_from") or {}).get(day) or {}).items()}


def on_from_for(rule_id: str, table: dict[str, str]) -> Optional[str]:
    if rule_id in table:
        return table[rule_id]
    for k, v in table.items():
        if k.endswith("*") and rule_id.startswith(k[:-1]):
            return v
    return None


def split_on_from(rows, table: dict[str, str]):
    """(desk rows, history rows): a row whose entry_min is before its rule's on-from minute is history."""
    keep, hist = [], []
    for r in rows:
        f = on_from_for(str(r.get("rule_id") or ""), table)
        (hist if f and str(r.get("entry_min") or "") < f else keep).append(r)
    return keep, hist


# 2026-10-21 entry-at-ask (desk book): paper_extra rows were booked at the 1m open (about half a spread too good).
# Rows from the fixed runner carry entry_px_1m_open + entry_src and are kept as-is. Older-format rows dated on/after
# DESK_ENTRY_ASK_FROM get open + half spread, labelled. Earlier days are history and are not changed.
DESK_HALF_SPREAD = {"NIFTY": 0.4977, "SENSEX": 2.8275}
DESK_ENTRY_ASK_FROM = os.environ.get("DESK_ENTRY_ASK_FROM", "2026-10-22")


def desk_entry_px(x: dict, und: str, day: str) -> tuple[float, str]:
    """(booked entry, source label) for one paper_extra row in the desk book."""
    px = float(x["entry_px"])
    if "entry_px_1m_open" in x:
        return px, str(x.get("entry_src") or "v2_ask")
    if day >= DESK_ENTRY_ASK_FROM and und in DESK_HALF_SPREAD:
        return round(px + DESK_HALF_SPREAD[und], 2), "1m_open+half_spread"
    return px, str(x.get("entry_src") or "dhan_api_1m")


def paper_extra_rows(root: Path, day: str, skip: Optional[set] = None) -> tuple[list, list]:
    """Rows written by scripts/paper_extra/runner.py (lab rule signals on real 1m option bars), shaped like
    desk research-rule rows. Missing/bad file -> no rows. Never a broker."""
    p = Path(root) / PAPER_EXTRA_REL / f"{day}.json"
    try:
        blob = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], []
    if blob.get("day") != day or blob.get("orders") != "REFUSED":
        return [], []
    skip = skip or set()
    opens, closed = [], []
    for x in blob.get("rows") or []:
        try:
            rid = str(x["rule_id"]); und = str(x.get("underlying") or "NIFTY")
            if (rid, und, x["signal_time"]) in skip:
                continue
            # 2026-10-19: only OPEN / CLOSED rows are ever booked. SKIPPED_CHASE (anti-chase), DATA_MISSING, PENDING etc. never are.
            if x.get("status") not in ("OPEN", "CLOSED"):
                continue
            is_closed = x["status"] == "CLOSED"
            mark = float(x["exit_px"] if is_closed else x["mark_px"])
            entry_px, entry_src = desk_entry_px(x, und, day)
            row = _trade_row(
                rule={"rule_id": rid, "source_config": f"paper_extra:{x['strategy']}", "family": "PAPER_EXTRA"},
                underlying=und, side=str(x["side"]), strike=float(x["strike"]), sig_min=str(x["signal_time"]),
                entry_min=str(x["entry_time"]), exit_min=str(x["exit_time"] if is_closed else x.get("mark_time") or x["entry_time"]),
                entry=entry_px, mark=mark, day=day,
                entry_bar={"source": entry_src},
                mark_bar={"hhmm": str(x["exit_time"] if is_closed else x.get("mark_time") or x["entry_time"]),
                          "source": x.get("exit_src") or x.get("entry_src") or "dhan_api_1m"},
                closed=is_closed, reason=x.get("exit_reason") or None)
        except (KeyError, TypeError, ValueError):
            continue
        row["strategy_name"] = str(x["strategy"])
        row["entry_src"] = entry_src
        if entry_px != float(x["entry_px"]) or "entry_px_1m_open" in x:
            row["entry_px_1m_open"] = x.get("entry_px_1m_open", x["entry_px"])
        row["stop_px"] = x.get("stop_px"); row["target_px"] = x.get("target_px")
        row["stop"] = x.get("stop_px"); row["target"] = x.get("target_px")
        row["exit_rule"] = x.get("exit_rule"); row["exit_time"] = x.get("exit_time")
        row["spec_exit_min"] = x.get("planned_exit_ist") or (x.get("exit_time") if not is_closed and x.get("exit_reason") == "TIME" else None)
        for k in ("index_stop", "stop_target_basis", "planned_exit_ist", "exit_reason_std", "official_open", "open_src",
                  "why", "trail", "safety_close_ist", "price_src"):   # 2026-10-19 price exits: reason + levels for the website
            if x.get(k) is not None:
                row[k] = x[k]
        row["justification"] = (f"paper_extra {x['strategy']}: {x.get('why') or 'lab rule signal'}; entry next-minute open. "
                                f"{x.get('exit_rule') or ''} NO_PROMOTE.")
        (closed if is_closed else opens).append(row)
    return opens, closed


def replay(
    root: Path,
    day: str,
    *,
    underlyings: Iterable[str] = UNDERLYINGS,
    rules: Optional[Sequence[dict[str, Any]]] = None,
    fill_v2: Optional[bool] = None,
    now_hhmm: Optional[str] = None,
    now_ts: Optional[float] = None,
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
    if rules is None:  # config/desk_rules_off.yaml: never a desk trade from the day after it was set
        off = desk_rules_off()
        moved = [r for r in live_rules if r["rule_id"] in off and r["rule_id"] not in entry_before]
        live_rules = [r for r in live_rules if r not in moved]
        shadow_rules += [r for r in moved if r not in shadow_rules]
    # 2026-10-12: V2 primary (incremental reads), legacy DUAL-TAPE fallback. DESK_RR_SOURCE=legacy reverts.
    source = os.environ.get("DESK_RR_SOURCE", "v2").strip().lower()
    if fill_v2 is None:
        fill_v2 = os.environ.get("DESK_RR_V2_FILL", "").strip() in {"1", "true", "yes", "on"}
    if source == "legacy":
        loader = load_minutes_filled if fill_v2 else load_atm_minutes
    else:
        loader = load_minutes_v2_primary
        fill_v2 = True
    bars_by = {und: loader(Path(root), und, day) for und in underlyings}
    from desk_ml import desk_risk

    risk_cfg = desk_risk.load_config()
    risk_cfg["_day"] = day  # day_stop_off_from lookup
    skip: set = set()
    blocked: list[dict[str, Any]] = []
    on_from_hist = None
    for _ in range(10):  # D6: re-run without blocked signals until the blocked set is stable
        opens, closed = [], []
        for und, bars in bars_by.items():
            o, c = replay_underlying(bars, underlying=und, day=day, rules=live_rules, skip=skip,
                                    entry_before=entry_before, now_hhmm=now_hhmm)
            opens.extend(o); closed.extend(c)
        if rules is None:  # 2026-10-13: paper_extra lab strategies go through the same desk guards
            xo, xc = paper_extra_rows(Path(root), day, skip)
            opens.extend(xo); closed.extend(xc)
            onf = rules_on_from(day)
            opens, ho = split_on_from(opens, onf); closed, hc = split_on_from(closed, onf)
            sho = desk_shadow_only(day)   # 2026-10-21: shadow-only rules never reach the desk guards (no slot, no cap, no P&L)
            if sho:
                opens, so = split_shadow_only(opens, sho); closed, sc = split_shadow_only(closed, sho)
                ho = ho + so; hc = hc + sc
            on_from_hist = (ho, hc)
        opens, closed, new_blocked, dup_shadow, taken = _desk_pass(
            opens, closed, day, [r["rule_id"] for r in live_rules], risk_cfg,
            q01_window=q01_priority_window(Path(root), day) if rules is None else None)
        blocked.extend(new_blocked)
        add = {(b["rule_id"], b["underlying"], b["sig_min"]) for b in new_blocked}
        if not add - skip:
            break
        skip |= add
    shadow_open, shadow_closed = [], []
    if rules is None and on_from_hist is not None:  # before switch-on: history, shadow only
        shadow_open.extend(on_from_hist[0]); shadow_closed.extend(on_from_hist[1])
    for und, bars in bars_by.items():
        o, c = replay_underlying(bars, underlying=und, day=day, rules=shadow_rules, now_hhmm=now_hhmm)
        shadow_open.extend(o); shadow_closed.extend(c)
    per = {und: {"n_minutes": len(bars_by[und]),
                 "n_open": sum(1 for r in opens if r["underlying"] == und),
                 "n_closed": sum(1 for r in closed if r["underlying"] == und)} for und in bars_by}
    uniq = {}
    for b in blocked:
        uniq[(b["rule_id"], b["underlying"], b["sig_min"])] = b
    _mark(opens, TRADED, shadow=False); _mark(closed, TRADED, shadow=False)
    _mark(shadow_open, SHADOW_PARKED, shadow=True); _mark(shadow_closed, SHADOW_PARKED, shadow=True)
    guard_rows = [b for b in uniq.values() if b.get("guard") in (BLOCKED_OPPOSITE_SIDE, BLOCKED_Q01_WINDOW, Q01_SKIPPED_CAP)]
    risk_rows = [b for b in uniq.values() if b.get("guard") in desk_risk.RISK_STATUSES]
    for b in guard_rows:
        _mark([b], b["guard"], shadow=True)
    for b in risk_rows:
        _mark([b], b["guard"], shadow=True)
    _mark(dup_shadow, DUP_SAME_CONTRACT, shadow=True)
    out = {
        "risk": desk_risk.state(taken, risk_cfg),
        "risk_blocked": risk_rows,
        "guard_blocked": guard_rows,
        "dup_same_contract": dup_shadow,
        "shadow_parked": {"rule_ids": [r["rule_id"] for r in shadow_rules], "open": shadow_open,
                          "closed": shadow_closed, "note": "PARKED rules: computed, not traded, not in desk P&L"},
        "enabled": True,
        "flag": FLAG_ENV,
        "rule_ids": [r["rule_id"] for r in live_rules],
        "underlyings": list(underlyings),
        "qty": dict(QTY),
        "lots": LOTS,
        "v2_fill": bool(fill_v2),
        "price_source": "legacy" if source == "legacy" else "v2_primary+dual_tape_fallback",
        "pricing": "ask-in / bid-out (mid fallback flagged), costs 1.5x #84",
        "open": opens,
        "closed": closed,
        "per_underlying": per,
        "execution": "refused",
        "orders": "REFUSED",
        "promote": False,
    }
    if now_ts is not None:
        apply_stale_guard(out, bars_by, now_ts)
    return out


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
        now = datetime.now(IST)
        # live day: the wall clock closes an H20 trade at its exit even if the tape is behind
        live = now.date().isoformat() == day
        result = replay(base, day, now_hhmm=now.strftime("%H:%M") if live else None,
                        now_ts=now.timestamp() if live else None)
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
        # not traded, not in desk P&L; each row carries desk_status + shadow=True
        "guard_blocked": result.get("guard_blocked") or [],
        "shadow_parked": result.get("shadow_parked") or {},
        "dup_same_contract": result.get("dup_same_contract") or [],
        "risk_blocked": result.get("risk_blocked") or [],
    }
    out["risk"] = result.get("risk")  # board.risk: halt state from the same gate (desk_risk.state)
    stale = result.get("price_staleness")
    if stale:
        out["price_staleness"] = stale
        out["research_rules"]["price_staleness"] = stale
        if stale.get("stale"):
            risk = dict(out.get("risk") or {})
            risk["stale_prices"] = True
            risk["halted_reason"] = risk.get("halted_reason") or desk_risk_stale()
            out["risk"] = risk
            out["alerts"] = list(out.get("alerts") or []) + [{"level": "WARN", "code": "STALE_PRICES",
                                                               "text": stale["alert"]}]
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


def desk_risk_stale() -> str:
    from desk_ml.desk_risk import RISK_STALE_PRICES

    return RISK_STALE_PRICES


def apply_stale_guard(result: dict[str, Any], bars_by: dict[str, dict[str, Any]], now_ts: Optional[float]) -> None:
    """Live only: staleness of the latest bar per index vs the wall clock. When stale, desk OPEN rows that
    entered at/after the newest priced minute (decided on stale data) move to risk_blocked RISK_STALE_PRICES."""
    from desk_ml import desk_risk

    if now_ts is None:
        return
    last = {u: (max((b.get("ts") or 0) for b in bars.values()) or None) if bars else None for u, bars in bars_by.items()}
    st = desk_risk.price_staleness(last, now_ts)
    result["price_staleness"] = st
    if not st["stale"]:
        return
    keep, moved = [], []
    for r in result.get("open") or []:
        bars = bars_by.get(r.get("underlying")) or {}
        newest = max(bars) if bars else ""
        if str(r.get("entry_min") or "") >= newest:
            b = dict(r); b["guard"] = desk_risk.RISK_STALE_PRICES; _mark([b], desk_risk.RISK_STALE_PRICES, shadow=True)
            moved.append(b)
        else:
            keep.append(r)
    result["open"] = keep
    result["risk_blocked"] = list(result.get("risk_blocked") or []) + moved


def publish_board(board: dict[str, Any], *, root: Path) -> None:
    from desk_ml.paper_scalp import write_dashboard

    write_dashboard(board, root=root)
