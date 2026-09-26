"""Shadow analysts: log a vote-like record, never a decision.

Each record has value, flag, confidence and reasoning. The boss drops any vote
with ``metadata.shadow`` (and any id listed ``shadow: true`` in config). They
read only bars and book state at this tick.

TODO: consolidation-box and sweep-and-reclaim event logging. No clean detector
for those events exists in this repo (``backtest_engine.fabio_proxy`` is a
strategy lean, not an event detector). Do not invent a trading rule here.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from analysts.base import ABSTAIN, Analyst, MarketContext, Vote
from analysts.registry import register

IST = timezone(timedelta(hours=5, minutes=30))
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


def dealer_gex(
    rows: Sequence[dict[str, Any]],
    spot: Optional[float],
    lot_size: Optional[float],
    *,
    convention: str = DEALER_LONG_CALLS_SHORT_PUTS,
) -> Optional[dict[str, Any]]:
    """Sum over strikes of gamma × OI × lot × spot² × 0.01.

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
    scale = lot_v * spot_v * spot_v * 0.01
    per: list[tuple[float, float]] = []
    for row in rows:
        strike = _num(row.get("strike"))
        if strike is None:
            continue
        gex = 0.0
        used = False
        ce_g, ce_oi = _num(row.get("ce_gamma")), _num(row.get("ce_oi"))
        pe_g, pe_oi = _num(row.get("pe_gamma")), _num(row.get("pe_oi"))
        if ce_g is not None and ce_oi is not None:
            gex += sign * ce_g * ce_oi * scale
            used = True
        if pe_g is not None and pe_oi is not None:
            gex -= sign * pe_g * pe_oi * scale
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
    return {"gex": total, "zero_gamma": zero, "regime": regime, "n_strikes": len(per)}


def _prior_daily(engine: Any, und: str, bars: Sequence[dict[str, Any]], session_date: str) -> list[dict[str, Any]]:
    stored = getattr(engine, "shadow_prior_daily", None) or {}
    prior = list(stored.get(und) or [])
    prior = [r for r in prior if str(r.get("date") or "") < session_date]
    extra = daily_from_intraday(bars, before_date=session_date)
    return merge_daily(prior, extra)


def _day_open(bars: Sequence[dict[str, Any]], session_date: str) -> Optional[float]:
    for bar in bars:
        try:
            if ist_date(int(bar["ts"])) != session_date:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        open_ = _num(bar.get("open"))
        if open_ is None:
            open_ = _num(bar.get("close"))
        return open_
    return None


def _prior_close(daily: Sequence[dict[str, Any]]) -> Optional[float]:
    if not daily:
        return None
    return _num(daily[-1].get("close"))


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


def late_momentum(bars: Sequence[dict[str, Any]], prior_close: Optional[float], now_ts: int) -> dict[str, Any]:
    """Sign of the completed 14:44 IST close versus the prior session close. Not known before 14:45."""
    now = ist_dt(now_ts)
    if (now.hour, now.minute) < (14, 45):
        return _skip("NOT_YET")
    if prior_close is None:
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
    prior_close = _prior_close(daily)
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
        open_ = _day_open(bars, session_date)
        if open_ is None or spot is None:
            out["day_direction"] = _skip("NO_DAY_OPEN")
        elif spot > open_:
            out["day_direction"] = _cell(spot - open_, "CE", "spot above day open; CE aligned", confidence=0.5, ce_allowed=True, pe_allowed=False)
        elif spot < open_:
            out["day_direction"] = _cell(spot - open_, "PE", "spot below day open; PE aligned", confidence=0.5, ce_allowed=False, pe_allowed=True)
        else:
            out["day_direction"] = _cell(0.0, "FLAT", "spot at day open", confidence=0.5, ce_allowed=False, pe_allowed=False)

    if not p["c4_enabled"]:
        out["late_day_momentum"] = _skip("DISABLED")
    else:
        out["late_day_momentum"] = late_momentum(bars, prior_close, now_ts)

    dates = expiry_dates()
    dte = days_to_expiry(session_date, dates) if dates else None
    if dte is None:
        out["expiry_day"] = _skip("EXPIRY_CALENDAR_UNKNOWN")
    else:
        out["expiry_day"] = _cell(dte, dte == 0, "dte from repo expiry calendar", confidence=0.5)

    gex = dealer_gex(_chain_rows(engine, tick, now_ts), spot, _lot_size(engine, und), convention=p["gex_convention"])
    if gex is None:
        why = "MISSING_CHAIN_OR_GREEKS" if p["gex_convention"] in {DEALER_LONG_CALLS_SHORT_PUTS, "short_calls_long_puts"} else "UNKNOWN_CONVENTION"
        out["gex"] = _skip(why)
    else:
        out["gex"] = _cell(
            gex["gex"], gex["regime"], f"dealer GEX {p['gex_convention']}", confidence=0.5,
            zero_gamma=gex["zero_gamma"], regime=gex["regime"], n_strikes=gex["n_strikes"],
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
