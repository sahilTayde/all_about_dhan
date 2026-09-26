"""Shadow analysts: log a vote-like record, never a decision.

Each record has value, flag, confidence and reasoning. The boss drops any vote
with ``metadata.shadow`` (and any id listed ``shadow: true`` in config). They
read only bars and book state at this tick.

TODO: consolidation-box and sweep-and-reclaim event logging. No clean detector
for those events exists in this repo (``backtest_engine.fabio_proxy`` is a
strategy lean, not an event detector). Do not invent a trading rule here.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from analysts.base import ABSTAIN, Analyst, MarketContext, Vote
from analysts.registry import register

log = logging.getLogger("analysts.shadow")

IST = timezone(timedelta(hours=5, minutes=30))
# Static list in trading_agents_india.index_ce_pe_formulas.default_expiry_tuesdays.
# It ends 2026-09-15. After that we extend by weekly Tuesdays and say so.
STATIC_EXPIRY_SOURCE = "default_expiry_tuesdays"
WEEKLY_EXPIRY_SOURCE = "weekly_tuesday_extension"
GEX_WINDOW_POINTS = 300.0
_CALENDAR_WARNED: set[str] = set()
MINUTES_PER_SESSION = 375  # 09:15–15:30 IST
SESSIONS_PER_YEAR = 252
ANN_FACTOR = math.sqrt(SESSIONS_PER_YEAR * MINUTES_PER_SESSION)
LOW_WEIGHT = 0.2  # er30 / br3_3m are log-only; confidence stays low
DEALER_LONG_CALLS_SHORT_PUTS = "long_calls_short_puts"

SHADOW_KEYS = (
    "rng60_atr",
    "rng5_3m",
    "rv30",
    "er30",
    "br3_3m",
    "chasing",
    "high_vol",
    "minutes_since_prior_trade",
    "day_direction",
    "late_day_momentum",
    "expiry_day",
    "gex",
)


def ist_dt(ts: int) -> datetime:
    return datetime.fromtimestamp(int(ts), IST)


def ist_date(ts: int) -> str:
    return ist_dt(ts).date().isoformat()


def _num(raw: Any) -> Optional[float]:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _dig(tree: Any, path: str, default: Any) -> Any:
    cur = tree if isinstance(tree, dict) else {}
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def shadow_params(cfg: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Config keys from config/analysts.yaml. Missing keys keep the lab defaults."""
    cfg = cfg or {}
    features = cfg.get("features") if isinstance(cfg.get("features"), dict) else {}
    shadow = cfg.get("shadow") if isinstance(cfg.get("shadow"), dict) else {}
    return {
        "rng60_window": int(_dig(features, "vol.rng60.window_min", 60)),
        "rng5_n": int(_dig(features, "vol.rng5_3m.n_bars", 5)),
        "rv30_window": int(_dig(features, "vol.rv30.window", 30)),
        "er30_window": int(_dig(features, "vol.er30.window", 30)),
        "br3_n": int(_dig(features, "vol.br3_3m.n_bars", 3)),
        "chasing_threshold": float(_dig(shadow, "chasing.threshold", 0.376)),
        "rv30_min": float(_dig(shadow, "high_vol.rv30_min", 10.06)),
        "c5_enabled": bool(_dig(shadow, "c5_trend_align.enabled", True)),
        "c4_enabled": bool(_dig(shadow, "c4_late_mom.enabled", True)),
        "gex_convention": str(_dig(shadow, "gex.dealer_convention", DEALER_LONG_CALLS_SHORT_PUTS)),
        "gex_window": float(_dig(shadow, "gex.window_points", GEX_WINDOW_POINTS)),
    }


def _cell(value: Any, flag: Any, reasoning: str, *, confidence: float = 0.0, **extra: Any) -> dict[str, Any]:
    return {"value": value, "flag": flag, "confidence": float(confidence), "reasoning": reasoning, "extra": extra}


def _skip(reasoning: str) -> dict[str, Any]:
    return _cell(None, None, reasoning, confidence=0.0)


def bars_upto(bars: Sequence[dict[str, Any]], now_ts: int) -> list[dict[str, Any]]:
    """Drop any bar whose timestamp is after this tick (look-ahead guard)."""
    out = []
    now = int(now_ts)
    for bar in bars:
        try:
            ts = int(bar["ts"])
        except (KeyError, TypeError, ValueError):
            continue
        if ts <= now:
            out.append(bar)
    return out


def daily_ohlc_from_closes(closes_by_ts: dict[Any, Any]) -> list[dict[str, Any]]:
    """One bar per IST date from a close series. High/low are the close range when true OHLC is absent."""
    by: dict[str, dict[str, Any]] = {}
    for raw_ts, raw_px in (closes_by_ts or {}).items():
        px = _num(raw_px)
        ts = _num(raw_ts)
        if px is None or ts is None:
            continue
        day = ist_date(int(ts))
        row = by.get(day)
        if row is None:
            by[day] = {"date": day, "high": px, "low": px, "close": px, "ts": int(ts)}
            continue
        row["high"] = max(float(row["high"]), px)
        row["low"] = min(float(row["low"]), px)
        if int(ts) >= int(row["ts"]):
            row["close"] = px
            row["ts"] = int(ts)
    return [by[d] for d in sorted(by)]


def daily_from_intraday(bars: Sequence[dict[str, Any]], *, before_date: Optional[str]) -> list[dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    for bar in bars:
        try:
            day = ist_date(int(bar["ts"]))
        except (KeyError, TypeError, ValueError):
            continue
        if before_date and day >= before_date:
            continue
        high, low = _bar_hl(bar)
        close = _num(bar.get("close"))
        if high is None or low is None or close is None:
            continue
        row = by.get(day)
        if row is None:
            by[day] = {"date": day, "high": high, "low": low, "close": close}
            continue
        row["high"] = max(float(row["high"]), high)
        row["low"] = min(float(row["low"]), low)
        row["close"] = close
    return [by[d] for d in sorted(by)]


def merge_daily(prior: Sequence[dict[str, Any]], extra: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """``extra`` (from the tape) overrides a close-only prior bar on the same date."""
    by = {str(r["date"]): r for r in prior if r.get("date")}
    for row in extra:
        if row.get("date"):
            by[str(row["date"])] = row
    return [by[d] for d in sorted(by)]


def wilder_atr(daily: Sequence[dict[str, Any]], period: int = 14) -> Optional[float]:
    """Wilder ATR on daily bars. Needs ``period + 1`` bars. Today's session is not included by the caller."""
    bars = list(daily)
    if period < 1 or len(bars) < period + 1:
        return None
    trs: list[float] = []
    for i, bar in enumerate(bars):
        high, low = _num(bar.get("high")), _num(bar.get("low"))
        close = _num(bar.get("close"))
        if high is None or low is None or close is None:
            return None
        if i == 0:
            trs.append(high - low)
        else:
            prev = _num(bars[i - 1].get("close"))
            if prev is None:
                return None
            trs.append(max(high - low, abs(high - prev), abs(low - prev)))
    atr = sum(trs[1 : period + 1]) / period
    for i in range(period + 1, len(bars)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr


def _bar_hl(bar: dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    close = _num(bar.get("close"))
    high = _num(bar.get("high"))
    low = _num(bar.get("low"))
    if high is None:
        high = close
    if low is None:
        low = close
    return high, low


def _closes(bars: Sequence[dict[str, Any]]) -> list[float]:
    out = []
    for bar in bars:
        px = _num(bar.get("close"))
        if px is None:
            return []
        out.append(px)
    return out


def complete_bars_3m(bars_1m: Sequence[dict[str, Any]], now_ts: int) -> list[dict[str, Any]]:
    """IST-epoch 3-minute buckets. The bucket still forming at ``now_ts`` is left out."""
    buckets: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    for bar in bars_upto(bars_1m, now_ts):
        ts = int(bar["ts"])
        key = ts - (ts % 180)
        high, low = _bar_hl(bar)
        close = _num(bar.get("close"))
        open_ = _num(bar.get("open"))
        if high is None or low is None or close is None:
            continue
        if open_ is None:
            open_ = close
        row = buckets.get(key)
        if row is None:
            order.append(key)
            buckets[key] = {"ts": key, "open": open_, "high": high, "low": low, "close": close}
            continue
        row["high"] = max(float(row["high"]), high)
        row["low"] = min(float(row["low"]), low)
        row["close"] = close
    now = int(now_ts)
    return [buckets[k] for k in order if k + 180 <= now]


def range_over_atr(bars: Sequence[dict[str, Any]], atr: Optional[float]) -> Optional[float]:
    if not bars or atr is None or atr <= 1e-12:
        return None
    highs, lows = [], []
    for bar in bars:
        high, low = _bar_hl(bar)
        if high is None or low is None:
            return None
        highs.append(high)
        lows.append(low)
    return (max(highs) - min(lows)) / atr


def log_returns(closes: Sequence[float]) -> Optional[list[float]]:
    out: list[float] = []
    for i in range(1, len(closes)):
        prev, cur = closes[i - 1], closes[i]
        if prev <= 0 or cur <= 0:
            return None
        out.append(math.log(cur / prev))
    return out


def realised_vol_pct(returns: Sequence[float]) -> Optional[float]:
    """Annualised percent. Sample stdev of 1-minute log returns × sqrt(252 × 375) × 100."""
    n = len(returns)
    if n < 2:
        return None
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    if var < 0:
        return None
    return math.sqrt(var) * ANN_FACTOR * 100.0


def efficiency_ratio(closes: Sequence[float]) -> Optional[float]:
    if len(closes) < 2:
        return None
    diffs = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    path = sum(abs(d) for d in diffs)
    net = abs(closes[-1] - closes[0])
    if path <= 1e-12:
        return 0.0 if net <= 1e-12 else None
    return net / path


def body_range(bar: dict[str, Any]) -> Optional[float]:
    high, low = _bar_hl(bar)
    open_, close = _num(bar.get("open")), _num(bar.get("close"))
    if high is None or low is None or open_ is None or close is None:
        return None
    span = high - low
    if span <= 1e-12:
        return 0.0
    return abs(close - open_) / span


def detect_oi_unit(values: Sequence[float], lot_size: float) -> str:
    """``shares`` when open interest is a lot multiple (Dhan tape); else ``contracts``.

    NSE lots cannot be fractional, so share OI divides by the lot. Contract counts
    usually do not. 80% of the positive prints deciding the chain is enough; one
    strike that happens to divide does not flip the rest.
    """
    lot = float(lot_size)
    positives = [v for v in values if v is not None and v > 0]
    if lot <= 1 or not positives:
        return "contracts"
    divisible = 0
    for oi in positives:
        q = oi / lot
        if abs(q - round(q)) < 1e-6:
            divisible += 1
    if divisible / len(positives) >= 0.8:
        return "shares"
    return "contracts"


def oi_to_contracts(oi: float, lot_size: float, unit: str) -> float:
    if unit == "shares" and lot_size > 0:
        return oi / float(lot_size)
    return oi


def dealer_gex(
    rows: Sequence[dict[str, Any]],
    spot: Optional[float],
    lot_size: Optional[float],
    *,
    convention: str = DEALER_LONG_CALLS_SHORT_PUTS,
    window_points: float = GEX_WINDOW_POINTS,
) -> Optional[dict[str, Any]]:
    """Sum over strikes of gamma × contract OI × lot × spot² × 0.01.

    Only strikes within ``window_points`` of spot are used (default ±300).
    OI that is in shares is divided by the lot first, so the lot is not applied twice.
    ``long_calls_short_puts``: dealers long calls and short puts, so call GEX is
    positive and put GEX is negative. Returns None when chain data or greeks are
    missing (caller skips; it does not invent a number).
    """
    spot_v, lot_v = _num(spot), _num(lot_size)
    if spot_v is None or lot_v is None or spot_v <= 0 or lot_v <= 0 or not rows:
        return None
    if convention == DEALER_LONG_CALLS_SHORT_PUTS:
        sign = 1.0
    elif convention == "short_calls_long_puts":
        sign = -1.0
    else:
        return None
    window = abs(float(window_points))
    usable: list[tuple[float, Optional[float], Optional[float], Optional[float], Optional[float]]] = []
    oi_values: list[float] = []
    for row in rows:
        strike = _num(row.get("strike"))
        if strike is None or abs(strike - spot_v) > window:
            continue
        ce_g, ce_oi = _num(row.get("ce_gamma")), _num(row.get("ce_oi"))
        pe_g, pe_oi = _num(row.get("pe_gamma")), _num(row.get("pe_oi"))
        usable.append((strike, ce_g, ce_oi, pe_g, pe_oi))
        if ce_oi is not None:
            oi_values.append(ce_oi)
        if pe_oi is not None:
            oi_values.append(pe_oi)
    hinted = None
    for row in rows:
        raw = row.get("oi_unit")
        if raw in ("shares", "contracts"):
            hinted = str(raw)
            break
    unit = hinted or detect_oi_unit(oi_values, lot_v)
    scale = lot_v * spot_v * spot_v * 0.01
    per: list[tuple[float, float]] = []
    for strike, ce_g, ce_oi, pe_g, pe_oi in usable:
        gex = 0.0
        used = False
        if ce_g is not None and ce_oi is not None:
            gex += sign * ce_g * oi_to_contracts(ce_oi, lot_v, unit) * scale
            used = True
        if pe_g is not None and pe_oi is not None:
            gex -= sign * pe_g * oi_to_contracts(pe_oi, lot_v, unit) * scale
            used = True
        if used:
            per.append((strike, gex))
    if not per:
        return None
    per.sort()
    total = sum(g for _s, g in per)
    zero: Optional[float] = None
    cum = 0.0
    prev_s: Optional[float] = None
    prev_c: Optional[float] = None
    for strike, gex in per:
        cum += gex
        if cum == 0:
            zero = strike
            break
        if prev_c is not None and prev_s is not None and prev_c * cum < 0:
            frac = abs(prev_c) / (abs(prev_c) + abs(cum))
            zero = prev_s + (strike - prev_s) * frac
            break
        if prev_c == 0 and prev_s is not None:
            zero = prev_s
            break
        prev_s, prev_c = strike, cum
    if total > 0:
        regime = "pos"
    elif total < 0:
        regime = "neg"
    else:
        regime = "flat"
    strikes = [s for s, _g in per]
    return {
        "gex": total,
        "zero_gamma": zero,
        "regime": regime,
        "n_strikes": len(per),
        "oi_unit": unit,
        "window_points": window,
        "strike_min": min(strikes) if strikes else None,
        "strike_max": max(strikes) if strikes else None,
    }


def _prior_daily(engine: Any, und: str, bars: Sequence[dict[str, Any]], session_date: str) -> list[dict[str, Any]]:
    stored = getattr(engine, "shadow_prior_daily", None) or {}
    prior = list(stored.get(und) or [])
    prior = [r for r in prior if str(r.get("date") or "") < session_date]
    extra = daily_from_intraday(bars, before_date=session_date)
    return merge_daily(prior, extra)


_INDEX_SIDS = {"NIFTY": "13", "BANKNIFTY": "25", "SENSEX": "51"}
_OHLC_OPEN_CACHE: dict[tuple[str, str, str], Optional[float]] = {}
_OHLC_MISS_AT: dict[tuple[str, str, str], float] = {}  # monotonic time of the last miss
OHLC_MISS_RETRY_S = 60.0


def _bar_open(bar: dict[str, Any]) -> Optional[float]:
    """The bar's open. A close is not an open, so a bar without one is skipped."""
    return _num(bar.get("open"))


def _in_session(dt: datetime, session_date: str) -> bool:
    """At or after 09:15 IST on this session. Midnight and pre-market prints carry yesterday's close."""
    return dt.date().isoformat() == session_date and (dt.hour, dt.minute) >= (9, 15)


def _ohlc_session_open(root: Path, underlying: str, session_date: str, now_ts: int) -> Optional[float]:
    """Open of the 09:15 IST bar in the saved index OHLC, if that bar is already known.

    A hit is cached. A miss is retried after ``OHLC_MISS_RETRY_S`` so a chart saved later in the
    live-loop process is picked up.
    """
    import time

    key = (str(root), underlying.upper(), session_date)
    if _OHLC_OPEN_CACHE.get(key) is not None:
        return _OHLC_OPEN_CACHE[key]
    missed = _OHLC_MISS_AT.get(key)
    if missed is not None and time.monotonic() - missed < OHLC_MISS_RETRY_S:
        return None
    found: Optional[float] = None
    sid = _INDEX_SIDS.get(underlying.upper())
    folder = root / "data" / "recon" / "ohlc"
    if sid and folder.is_dir():
        for path in sorted(folder.glob(f"INDEX_IDX_I_{sid}_1_*.json")):
            try:
                blob = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            data = blob.get("data") if isinstance(blob.get("data"), dict) else blob
            if not isinstance(data, dict):
                continue
            ts = data.get("timestamp") or data.get("time") or []
            opens = data.get("open") or data.get("Open") or []
            for i in range(min(len(ts), len(opens))):
                try:
                    stamp = int(ts[i])
                    px = float(opens[i])
                except (TypeError, ValueError):
                    continue
                if stamp > int(now_ts):
                    continue
                dt = ist_dt(stamp)
                if dt.date().isoformat() == session_date and (dt.hour, dt.minute) == (9, 15):
                    found = px
                    break
            if found is not None:
                break
    if found is None:
        _OHLC_MISS_AT[key] = time.monotonic()
    else:
        _OHLC_OPEN_CACHE[key] = found
        _OHLC_MISS_AT.pop(key, None)
    return found


def session_open(
    bars: Sequence[dict[str, Any]],
    session_date: str,
    *,
    quote_open: Optional[float] = None,
    ohlc_open: Optional[float] = None,
) -> tuple[Optional[float], Optional[str]]:
    """(price, open_source). Quote or the OHLC 09:15 open, else the first session bar's open.

    Only bars at or after 09:15 IST count: a 00:00 or pre-market print carries the previous
    close. Tapes that arm at 09:30 have no 09:15 bar. That fallback is logged as
    ``fallback_first_bar`` so it is not a silent substitute for the session open.
    """
    if quote_open is not None:
        return float(quote_open), "quote"
    if ohlc_open is not None:
        return float(ohlc_open), "ohlc"
    first: Optional[float] = None
    for bar in bars:
        try:
            dt = ist_dt(int(bar["ts"]))
        except (KeyError, TypeError, ValueError, OSError):
            continue
        if not _in_session(dt, session_date):
            continue
        px = _bar_open(bar)
        if px is None:
            continue
        if (dt.hour, dt.minute) == (9, 15):
            return px, "bar_0915"
        if first is None:
            first = px
    if first is not None:
        return first, "fallback_first_bar"
    return None, None


def _day_open(bars: Sequence[dict[str, Any]], session_date: str) -> Optional[float]:
    """09:15 IST open when that bar is in the series. Otherwise None (see ``session_open``)."""
    px, source = session_open(bars, session_date)
    if source == "bar_0915":
        return px
    return None


def _previous_weekday(day: date) -> date:
    d = day - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _prior_close_state(daily: Sequence[dict[str, Any]], session_date: str) -> tuple[Optional[float], str]:
    """(close, status). status is ok, missing, or stale (more than one weekday back)."""
    if not daily:
        return None, "missing"
    last = daily[-1]
    close = _num(last.get("close"))
    raw = str(last.get("date") or "")[:10]
    try:
        last_day = datetime.fromisoformat(raw).date()
        session = datetime.fromisoformat(session_date).date()
    except ValueError:
        return None, "missing"
    if close is None or last_day >= session:
        return None, "missing"
    if last_day < _previous_weekday(session):
        return None, "stale"
    return close, "ok"


def _last_trade_ts(engine: Any, und: str, now_ts: int) -> Optional[int]:
    best: Optional[int] = None
    now = int(now_ts)
    for row in getattr(engine, "closed", None) or []:
        if str(row.get("underlying") or "").upper() != und:
            continue
        ts = _num(row.get("closed_ts"))
        if ts is None:
            continue
        its = int(ts)
        if its <= now and (best is None or its > best):
            best = its
    opens = getattr(engine, "opens", None) or {}
    for key, pos in opens.items():
        u = key[1] if isinstance(key, tuple) and len(key) > 1 else getattr(pos, "underlying", None)
        if str(u or "").upper() != und:
            continue
        ts = _num(getattr(pos, "opened_ts", None))
        if ts is None:
            continue
        its = int(ts)
        if its <= now and (best is None or its > best):
            best = its
    return best


def _lot_size(engine: Any, und: str) -> Optional[float]:
    raw = (getattr(engine, "lot_by_und", None) or {}).get(und)
    if isinstance(raw, tuple):
        raw = raw[0]
    return _num(raw)


def _chain_rows(engine: Any, tick: Any, now_ts: int) -> list[dict[str, Any]]:
    extra = getattr(engine, "live_chain_rows", None)
    if extra:
        rows = _normalize_chain(extra, now_ts)
        if rows:
            return rows
    wings = getattr(tick, "wing_quotes", None)
    if isinstance(wings, dict):
        return _normalize_wings(wings)
    return []


def _row_ts(row: dict[str, Any]) -> Optional[int]:
    for key in ("ts", "timestamp"):
        raw = row.get(key)
        if raw is None:
            continue
        num = _num(raw)
        if num is not None:
            return int(num if num < 1e12 else num / 1000.0)
        text = str(raw).strip()
        if not text:
            continue
        try:
            return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
        except ValueError:
            continue
    return None


def _normalize_chain(rows: Any, now_ts: int) -> list[dict[str, Any]]:
    if hasattr(rows, "strikes"):
        rows = [
            {
                "strike": getattr(r, "strike", None),
                "ce_gamma": getattr(r, "ce_gamma", None),
                "pe_gamma": getattr(r, "pe_gamma", None),
                "ce_oi": getattr(r, "ce_oi", None),
                "pe_oi": getattr(r, "pe_oi", None),
                "ts": getattr(rows, "as_of_ist", None),
            }
            for r in rows.strikes
        ]
    merged: dict[float, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        ts = _row_ts(row)
        if ts is not None and ts > int(now_ts):
            continue
        strike = _num(row.get("strike"))
        if strike is None:
            continue
        side = str(row.get("option_type") or "").upper()
        slot = merged.setdefault(strike, {"strike": strike, "ce_gamma": None, "pe_gamma": None, "ce_oi": None, "pe_oi": None})
        ce_g = row.get("ce_gamma", row.get("gamma") if side == "CE" else None)
        pe_g = row.get("pe_gamma", row.get("gamma") if side == "PE" else None)
        ce_oi = row.get("ce_oi", row.get("open_interest") if side == "CE" else None)
        pe_oi = row.get("pe_oi", row.get("open_interest") if side == "PE" else None)
        if ce_g is not None:
            slot["ce_gamma"] = ce_g
        if pe_g is not None:
            slot["pe_gamma"] = pe_g
        if ce_oi is not None:
            slot["ce_oi"] = ce_oi
        if pe_oi is not None:
            slot["pe_oi"] = pe_oi
    return list(merged.values())


def _normalize_wings(wings: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for key, cell in wings.items():
        if not isinstance(cell, dict):
            continue
        strike = _num(key)
        if strike is None:
            continue
        out.append({
            "strike": strike,
            "ce_gamma": cell.get("ce_gamma"),
            "pe_gamma": cell.get("pe_gamma"),
            "ce_oi": cell.get("ce_oi"),
            "pe_oi": cell.get("pe_oi"),
        })
    return out


def _parse_day(raw: Any) -> Optional[str]:
    text = str(raw or "").strip()[:10]
    if len(text) < 10:
        return None
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return None
    return text


def _as_of_ts(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    num = _num(raw)
    if num is not None:
        return int(num if num < 1e12 else num / 1000.0)
    text = str(raw).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return int(dt.timestamp())


def _add_expiry(found: list[str], raw: Any) -> None:
    day = _parse_day(raw)
    if day and day not in found:
        found.append(day)


def expiries_on_tick(engine: Any, tick: Any, underlying: str, now_ts: int, session_date: str) -> list[str]:
    """This index's chain expiries only. A NIFTY Tuesday list is not applied here."""
    und = str(underlying or "").upper()
    found: list[str] = []
    stored = getattr(engine, "shadow_expiries", None)
    if isinstance(stored, dict):
        raw = stored.get(und)
        if isinstance(raw, (list, tuple)):
            for item in raw:
                _add_expiry(found, item)
        else:
            _add_expiry(found, raw)
    _add_expiry(found, getattr(tick, "expiry", None))
    chain = getattr(engine, "live_chain_rows", None)
    if isinstance(chain, dict):
        cu = str(chain.get("underlying") or "").upper()
        if not cu or cu == und:
            _add_expiry(found, chain.get("expiry"))
    elif chain is not None and str(getattr(chain, "underlying", "") or "").upper() in {"", und}:
        _add_expiry(found, getattr(chain, "expiry", None))
    for row in _chain_rows(engine, tick, now_ts):
        ru = str(row.get("underlying") or "").upper()
        if ru and ru != und:
            continue
        _add_expiry(found, row.get("expiry"))
    root = getattr(engine, "root", None)
    if root:
        found.extend(_expiries_from_saved(Path(root), und, now_ts, session_date, found))
    return found


def _expiries_from_saved(
    root: Path, underlying: str, now_ts: int, session_date: str, already: list[str]
) -> list[str]:
    """Chain snapshot JSON and the recorder's option-chain jsonl. Rows after this tick are ignored."""
    extra: list[str] = []
    und = underlying.upper()
    snap_dir = root / "data" / "desk_intel" / "snapshots" / und
    paths = []
    last = snap_dir / "last.json"
    if last.is_file():
        paths.append(last)
    day_dir = snap_dir / session_date
    if day_dir.is_dir():
        paths.extend(sorted(day_dir.glob("*.json")))
    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(raw, dict):
            continue
        as_of = _as_of_ts(raw.get("as_of_ist") or raw.get("ts"))
        if as_of is not None and as_of > int(now_ts):
            continue
        _add_expiry(extra, raw.get("expiry"))
    ymd = session_date.replace("-", "")
    jsonl = root / "data" / "recon" / "option_chain" / f"{ymd}.jsonl"
    if jsonl.is_file():
        try:
            lines = jsonl.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for line in lines:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            ts = _as_of_ts(rec.get("timestamp") or rec.get("ts"))
            if ts is not None and ts > int(now_ts):
                continue
            row_und = str(rec.get("underlying") or "").upper()
            if row_und != und:
                continue
            _add_expiry(extra, rec.get("expiry"))
    return [d for d in extra if d not in already]


def extend_weekly_tuesdays(static: Sequence[str], session_date: str) -> tuple[list[str], bool]:
    """After the static list runs out, keep weekly Tuesdays going. Holidays can still shift a week."""
    days: list[date] = []
    for raw in static:
        parsed = _parse_day(raw)
        if parsed:
            days.append(datetime.fromisoformat(parsed).date())
    if not days:
        return [], False
    last = max(days)
    try:
        session = datetime.fromisoformat(session_date).date()
    except ValueError:
        return [d.isoformat() for d in sorted(set(days))], False
    if session <= last:
        return [d.isoformat() for d in sorted(set(days))], False
    cursor = last
    horizon = session + timedelta(days=14)
    while cursor < horizon:
        cursor = cursor + timedelta(days=7)
        days.append(cursor)
    return [d.isoformat() for d in sorted(set(days))], True


def resolve_expiries(
    engine: Any, tick: Any, underlying: str, now_ts: int, session_date: str
) -> tuple[list[str], str, bool]:
    """(dates, source, static_calendar_exhausted).

    A chain expiry for this index is used alone. The weekly-Tuesday list is a NIFTY
    fallback only, and only when NIFTY has no chain expiry. Other indices do not borrow it.
    Warns once per session when that NIFTY list has run out.
    """
    und = str(underlying or "").upper()
    chain = expiries_on_tick(engine, tick, und, now_ts, session_date)
    if chain:
        return sorted(set(chain)), "chain", False
    if und != "NIFTY":
        return [], "no_index_expiry", False
    static = expiry_dates()
    extended, exhausted = extend_weekly_tuesdays(static, session_date)
    if exhausted and session_date not in _CALENDAR_WARNED:
        _CALENDAR_WARNED.add(session_date)
        last = static[-1] if static else "none"
        log.warning(
            "EXPIRY CALENDAR EXHAUSTED after %s (session %s, source %s). "
            "NIFTY is using weekly Tuesdays because this tick has no chain expiry. "
            "Other indices are not given this calendar. A holiday shift will not match it.",
            last, session_date, STATIC_EXPIRY_SOURCE,
        )
    source = WEEKLY_EXPIRY_SOURCE if exhausted else STATIC_EXPIRY_SOURCE
    return extended, source, exhausted


def expiry_dates() -> list[str]:
    """Repo expiry calendar (NIFTY weekly Tuesdays in the cache vintage). Empty if it cannot be imported."""
    try:
        from trading_agents_india.index_ce_pe_formulas import default_expiry_tuesdays
    except ImportError:
        return []
    return [str(d) for d in default_expiry_tuesdays()]


def days_to_expiry(session_date: str, dates: Sequence[str]) -> Optional[int]:
    """Calendar days until the next listed expiry on or after ``session_date``. None if the calendar doesn't cover it."""
    try:
        day = datetime.fromisoformat(session_date).date()
    except ValueError:
        return None
    future = []
    for raw in dates:
        try:
            exp = datetime.fromisoformat(str(raw)[:10]).date()
        except ValueError:
            continue
        if exp >= day:
            future.append(exp)
    if not future:
        return None
    return (min(future) - day).days


def late_momentum(
    bars: Sequence[dict[str, Any]],
    prior_close: Optional[float],
    now_ts: int,
    *,
    prior_state: str = "ok",
) -> dict[str, Any]:
    """Sign of the completed 14:44 IST close versus the prior session close. Not known before 14:45.

    A prior close older than the previous weekday is stale: log it as missing, do not invent a sign.
    """
    now = ist_dt(now_ts)
    if (now.hour, now.minute) < (14, 45):
        return _skip("NOT_YET")
    if prior_state == "stale":
        return _skip("STALE_PRIOR_CLOSE")
    if prior_close is None or prior_state == "missing":
        return _skip("MISSING_PRIOR_CLOSE")
    bar = None
    for row in bars_upto(bars, now_ts):
        dt = ist_dt(int(row["ts"]))
        if dt.hour == 14 and dt.minute == 44:
            bar = row
    if bar is None:
        return _skip("NO_1444_BAR")
    close = _num(bar.get("close"))
    if close is None:
        return _skip("NO_1444_BAR")
    if close > prior_close:
        sign = 1
    elif close < prior_close:
        sign = -1
    else:
        sign = 0
    return _cell(sign, sign, f"14:44 close {close} vs prior {prior_close}", confidence=0.5, close_1444=close)


def build_shadow_snapshot(engine: Any, step: Any, shadow_cfg: Optional[dict[str, Any]] = None) -> dict[str, dict[str, Any]]:
    """One point-in-time pack for every shadow analyst. Never raises."""
    try:
        return _build_shadow_snapshot(engine, step, shadow_cfg)
    except Exception as exc:  # a shadow bug must not change the decision path
        reason = f"SNAPSHOT_ERROR:{type(exc).__name__}"
        return {key: _skip(reason) for key in SHADOW_KEYS}


def _build_shadow_snapshot(engine: Any, step: Any, shadow_cfg: Optional[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    p = shadow_params(shadow_cfg)
    und = str(getattr(step, "und", "") or "").upper()
    tick = step.tick
    now_ts = int(tick.ts)
    bars = bars_upto(list(getattr(step, "bars_1m", None) or []), now_ts)
    session_date = ist_date(now_ts)
    spot = _num(getattr(tick, "idx_close", None))
    daily = _prior_daily(engine, und, bars, session_date)
    atr = wilder_atr(daily, 14)
    prior_close, prior_state = _prior_close_state(daily, session_date)
    out: dict[str, dict[str, Any]] = {}

    window = bars[-p["rng60_window"]:] if len(bars) >= p["rng60_window"] else []
    ratio = range_over_atr(window, atr)
    if ratio is None:
        rng_cell = _skip("NEED_60_BARS_AND_ATR14" if len(bars) < p["rng60_window"] or atr is None else "NO_RANGE")
    else:
        expected = ratio * float(atr)
        rng_cell = _cell(ratio, None, f"60m range / ATR14 ({atr:.4f})", confidence=0.5, expected_abs_move_pts=expected, atr14=atr)
    out["rng60_atr"] = rng_cell

    bars3 = complete_bars_3m(bars, now_ts)
    last5 = bars3[-p["rng5_n"]:] if len(bars3) >= p["rng5_n"] else []
    ratio5 = range_over_atr(last5, atr)
    if ratio5 is None:
        out["rng5_3m"] = _skip("NEED_5_3M_BARS_AND_ATR14")
    else:
        out["rng5_3m"] = _cell(ratio5, None, "5×3m range / ATR14", confidence=0.5, atr14=atr)

    rv_closes = _closes(bars[-(p["rv30_window"] + 1):])
    rets = log_returns(rv_closes) if len(rv_closes) >= p["rv30_window"] + 1 else None
    rv = realised_vol_pct(rets[-p["rv30_window"]:]) if rets and len(rets) >= p["rv30_window"] else None
    if rv is None:
        out["rv30"] = _skip("NEED_30_LOG_RETURNS")
    else:
        out["rv30"] = _cell(rv, None, "annualised % rv of 1m log returns", confidence=0.5)

    er_closes = _closes(bars[-(p["er30_window"] + 1):])
    er = efficiency_ratio(er_closes) if len(er_closes) >= p["er30_window"] + 1 else None
    if er is None:
        out["er30"] = _skip("NEED_30_MOVES")
    else:
        out["er30"] = _cell(er, None, "efficiency ratio, log only", confidence=LOW_WEIGHT)

    last3 = bars3[-p["br3_n"]:] if len(bars3) >= p["br3_n"] else []
    ratios = [body_range(b) for b in last3]
    if len(last3) < p["br3_n"] or any(r is None for r in ratios):
        out["br3_3m"] = _skip("NEED_3_3M_BARS")
    else:
        avg = sum(r for r in ratios if r is not None) / len(ratios)
        out["br3_3m"] = _cell(avg, None, "mean body/range, log only", confidence=LOW_WEIGHT)

    rng_v = rng_cell.get("value")
    if rng_v is None:
        out["chasing"] = _skip("NEED_RNG60_ATR")
    else:
        flag = bool(rng_v > p["chasing_threshold"])
        out["chasing"] = _cell(rng_v, flag, f"rng60_atr > {p['chasing_threshold']}", confidence=0.5)

    rv_v = out["rv30"].get("value")
    if rv_v is None:
        out["high_vol"] = _skip("NEED_RV30")
    else:
        flag = bool(rv_v > p["rv30_min"])
        out["high_vol"] = _cell(rv_v, flag, f"rv30 > {p['rv30_min']}", confidence=0.5)

    last_ts = _last_trade_ts(engine, und, now_ts)
    if last_ts is None:
        out["minutes_since_prior_trade"] = _skip("NO_PRIOR_TRADE")
    else:
        mins = (now_ts - last_ts) / 60.0
        out["minutes_since_prior_trade"] = _cell(mins, None, "minutes since last book trade", confidence=0.5)

    if not p["c5_enabled"]:
        out["day_direction"] = _skip("DISABLED")
    else:
        root = getattr(engine, "root", None)
        ohlc_open = _ohlc_session_open(Path(root), und, session_date, now_ts) if root else None
        quote_open = _num(getattr(tick, "day_open", None))
        if quote_open is not None and not _in_session(ist_dt(int(now_ts)), session_date):
            quote_open = None  # a pre-market quote's day open is yesterday's close
        open_, open_source = session_open(bars, session_date, quote_open=quote_open, ohlc_open=ohlc_open)
        if open_ is None or spot is None:
            out["day_direction"] = _skip("NO_DAY_OPEN")
        elif spot > open_:
            out["day_direction"] = _cell(
                spot - open_, "CE", f"spot above day open ({open_source}); CE aligned",
                confidence=0.5, ce_allowed=True, pe_allowed=False, open_source=open_source, day_open=open_,
            )
        elif spot < open_:
            out["day_direction"] = _cell(
                spot - open_, "PE", f"spot below day open ({open_source}); PE aligned",
                confidence=0.5, ce_allowed=False, pe_allowed=True, open_source=open_source, day_open=open_,
            )
        else:
            out["day_direction"] = _cell(
                0.0, "FLAT", f"spot at day open ({open_source})",
                confidence=0.5, ce_allowed=False, pe_allowed=False, open_source=open_source, day_open=open_,
            )

    if not p["c4_enabled"]:
        out["late_day_momentum"] = _skip("DISABLED")
    else:
        out["late_day_momentum"] = late_momentum(bars, prior_close, now_ts, prior_state=prior_state)

    dates, expiry_source, exhausted = resolve_expiries(engine, tick, und, now_ts, session_date)
    dte = days_to_expiry(session_date, dates) if dates else None
    if dte is None:
        if expiry_source == "no_index_expiry":
            why = "NO_INDEX_EXPIRY"
        elif exhausted:
            why = "EXPIRY_CALENDAR_EXHAUSTED"
        else:
            why = "EXPIRY_CALENDAR_UNKNOWN"
        out["expiry_day"] = _skip(why)
    else:
        out["expiry_day"] = _cell(
            dte, dte == 0, f"dte from {expiry_source}", confidence=0.5, expiry_source=expiry_source,
        )

    gex = dealer_gex(
        _chain_rows(engine, tick, now_ts), spot, _lot_size(engine, und),
        convention=p["gex_convention"], window_points=p["gex_window"],
    )
    if gex is None:
        why = "MISSING_CHAIN_OR_GREEKS" if p["gex_convention"] in {DEALER_LONG_CALLS_SHORT_PUTS, "short_calls_long_puts"} else "UNKNOWN_CONVENTION"
        out["gex"] = _skip(why)
    else:
        out["gex"] = _cell(
            gex["gex"], gex["regime"],
            (
                f"dealer GEX {p['gex_convention']} oi={gex['oi_unit']} "
                f"strikes {gex['strike_min']}-{gex['strike_max']} "
                f"window=±{gex['window_points']:g} n={gex['n_strikes']}"
            ),
            confidence=0.5,
            zero_gamma=gex["zero_gamma"], regime=gex["regime"], n_strikes=gex["n_strikes"],
            oi_unit=gex["oi_unit"], window_points=gex["window_points"],
            strike_min=gex["strike_min"], strike_max=gex["strike_max"],
        )
    return out


def vote_from_snapshot(analyst_id: str, ctx: MarketContext) -> Vote:
    snap = (ctx.features or {}).get("shadow") or {}
    cell = snap.get(analyst_id) or _skip("FEATURE_MISSING")
    extra = dict(cell.get("extra") or {})
    meta = {
        "shadow": True,
        "value": cell.get("value"),
        "flag": cell.get("flag"),
        "reason_class": "SHADOW",
        "silent": True,
        **extra,
    }
    conf = cell.get("confidence")
    try:
        confidence = float(conf if conf is not None else 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = min(1.0, max(0.0, confidence))
    return Vote(analyst_id, ABSTAIN, confidence, str(cell.get("reasoning") or ""), meta)


class ShadowAnalyst(Analyst):
    def __init__(self, key: str) -> None:
        self.analyst_id = key

    def vote(self, context: MarketContext) -> Vote:
        return vote_from_snapshot(self.analyst_id, context)


def _factory(key: str):
    def make() -> ShadowAnalyst:
        return ShadowAnalyst(key)

    return make


for _key in SHADOW_KEYS:
    register(_key, _factory(_key))
