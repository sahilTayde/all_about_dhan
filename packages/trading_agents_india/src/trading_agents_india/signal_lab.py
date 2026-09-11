"""Signal lab: grid-evaluate premium-tape entry rules across timeframes/overlays.

Founder ask (2026-09-11): test the strategies across timeframes (1/3/5/10m),
indices, premium series, trend gates, volume profile, and support/resistance;
generate signals per combination and validate them. This module is the
research harness: it replays persisted rolling ATM 1m premium tape
(premium_tape.py files), emits rising-edge signals per (timeframe, gate,
overlay) combination, and scores each signal by forward premium movement.

Honest scope: gross premium points, no brokerage/slippage/fills, rolling ATM
series (strike follows spot), research-only. Metrics here are backtest
measurements, never customer claims. No orders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from trading_agents_india.premium_tape import (
    IST,
    TapeBar,
    _ema,
    _in_window,
    _session_vwap,
    _sma,
    _supertrend_direction,
    _vwma,
)

GATES = ("dual_full", "dual_novol", "mrr_vwap", "ema_trend", "pullback")
OVERLAYS = ("none", "sr", "vp", "sr+vp")
TIMEFRAMES = (1, 3, 5, 10)
HORIZONS_MIN = (15, 30)

OPENING_RANGE_MIN = 15
NO_ENTRY_AFTER_MIN = 15 * 60  # 15:00 IST — leave room to measure forward returns
VP_BUCKETS = 40


def resample(bars: list[TapeBar], minutes: int) -> list[TapeBar]:
    """Aggregate 1m bars into `minutes` buckets aligned to IST clock."""
    if minutes <= 1:
        return list(bars)
    out: list[TapeBar] = []
    bucket: list[TapeBar] = []
    bucket_key: Optional[int] = None
    for bar in bars:
        dt = datetime.fromtimestamp(bar.ts, tz=IST)
        key = (dt.hour * 60 + dt.minute) // minutes
        day_key = dt.date().toordinal() * 10000 + key
        if bucket_key is None or day_key != bucket_key:
            if bucket:
                out.append(_merge(bucket))
            bucket = [bar]
            bucket_key = day_key
        else:
            bucket.append(bar)
    if bucket:
        out.append(_merge(bucket))
    return out


def _merge(bucket: list[TapeBar]) -> TapeBar:
    return TapeBar(
        ts=bucket[0].ts,
        open=bucket[0].open,
        high=max(b.high for b in bucket),
        low=min(b.low for b in bucket),
        close=bucket[-1].close,
        volume=sum(b.volume for b in bucket),
    )


def opening_range(bars_1m: list[TapeBar], minutes: int = OPENING_RANGE_MIN) -> Optional[tuple[float, float]]:
    """(high, low) of the first `minutes` 1m bars of the session."""
    if not bars_1m:
        return None
    first = bars_1m[: minutes]
    if len(first) < minutes:
        return None
    return max(b.high for b in first), min(b.low for b in first)


def volume_profile_poc(bars_1m: list[TapeBar], buckets: int = VP_BUCKETS) -> Optional[float]:
    """Point of control: mid-price of the volume-heaviest price bucket so far."""
    if not bars_1m:
        return None
    lo = min(b.low for b in bars_1m)
    hi = max(b.high for b in bars_1m)
    if hi <= lo:
        return lo
    width = (hi - lo) / buckets
    vols = [0.0] * buckets
    for b in bars_1m:
        typical = (b.high + b.low + b.close) / 3.0
        idx = min(buckets - 1, max(0, int((typical - lo) / width)))
        vols[idx] += b.volume if b.volume > 0 else 1.0
    best = max(range(buckets), key=lambda i: vols[i])
    return lo + (best + 0.5) * width


def _minute_of(ts: int) -> int:
    t = datetime.fromtimestamp(ts, tz=IST).time()
    return t.hour * 60 + t.minute


def gate_series(bars: list[TapeBar], gate: str) -> list[bool]:
    """Per-bar boolean for one gate variant on a (possibly resampled) series."""
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    mrr = _vwma(bars, 20)
    vwap = _session_vwap(bars)
    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    vol_ma = _sma(volumes, 20)
    st_dir = _supertrend_direction(bars, 10, 3.0)
    out: list[bool] = []
    for i, bar in enumerate(bars):
        base_ok = mrr[i] is not None and vwap[i] is not None
        if gate == "dual_full":
            ok = (
                base_ok
                and None not in (ema9[i], ema21[i], vol_ma[i], st_dir[i])
                and bar.close > mrr[i]
                and bar.close > vwap[i]
                and st_dir[i] == -1
                and ema9[i] > ema21[i]
                and bar.volume > vol_ma[i] * 1.3
                and _in_window(bar.ts)
            )
        elif gate == "dual_novol":
            ok = (
                base_ok
                and None not in (ema9[i], ema21[i], st_dir[i])
                and bar.close > mrr[i]
                and bar.close > vwap[i]
                and st_dir[i] == -1
                and ema9[i] > ema21[i]
                and _in_window(bar.ts)
            )
        elif gate == "mrr_vwap":
            ok = base_ok and bar.close > mrr[i] and bar.close > vwap[i]
        elif gate == "ema_trend":
            ok = (
                vwap[i] is not None
                and None not in (ema9[i], ema21[i])
                and ema9[i] > ema21[i]
                and bar.close > vwap[i]
            )
        elif gate == "pullback":
            # Buy the dip inside an uptrend instead of the breakout: trend up
            # (EMA9>EMA21, above VWAP) but price pulled back to/below EMA9.
            ok = (
                vwap[i] is not None
                and None not in (ema9[i], ema21[i])
                and ema9[i] > ema21[i]
                and bar.close > vwap[i]
                and bar.close <= ema9[i]
            )
        else:
            raise ValueError(f"unknown gate {gate}")
        out.append(bool(ok))
    return out


def overlay_ok(
    overlay: str,
    bar: TapeBar,
    bars_1m_so_far: list[TapeBar],
    or_levels: Optional[tuple[float, float]],
) -> bool:
    """Overlay filters use 1m session context regardless of signal timeframe."""
    if overlay == "none":
        return True
    checks: list[bool] = []
    if "sr" in overlay:
        # Support/resistance: long entries only on acceptance above the
        # opening-range high (resistance broken), classic session S/R.
        checks.append(or_levels is not None and bar.close > or_levels[0])
    if "vp" in overlay:
        poc = volume_profile_poc(bars_1m_so_far)
        checks.append(poc is not None and bar.close > poc)
    return all(checks)


SHELL_SL_PCT = 25.0
SHELL_TP_PCT = 50.0  # marketplace-common 1:2 premium shell — parameter, not truth


@dataclass
class SignalRecord:
    day: str
    underlying: str
    side: str
    timeframe: int
    gate: str
    overlay: str
    signal_ts: int
    signal_ist: str
    entry_price: float
    fwd: dict[str, Optional[float]]  # {"ret_15": pts, "ret_pct_15": %, ...}
    mfe_30: Optional[float]
    mae_30: Optional[float]
    shell_pl_pct: Optional[float] = None  # SL25/TP50 replay to EOD

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def shell_outcome(
    bars_1m: list[TapeBar],
    entry_idx: int,
    entry: float,
    *,
    sl_pct: float = SHELL_SL_PCT,
    tp_pct: float = SHELL_TP_PCT,
) -> Optional[float]:
    """Replay a fixed SL/TP percent shell from entry; stop-first on same-bar
    touch (conservative, same as backtest_mrr); EOD close exit otherwise."""
    if entry <= 0 or entry_idx >= len(bars_1m):
        return None
    stop = entry * (1.0 - sl_pct / 100.0)
    target = entry * (1.0 + tp_pct / 100.0)
    for bar in bars_1m[entry_idx:]:
        if bar.low <= stop:
            return -sl_pct
        if bar.high >= target:
            return tp_pct
    last = bars_1m[-1].close
    return round(100.0 * (last - entry) / entry, 2)


def _forward_stats(bars_1m: list[TapeBar], entry_idx: int, entry: float) -> tuple[dict[str, Optional[float]], Optional[float], Optional[float]]:
    fwd: dict[str, Optional[float]] = {}
    horizon_max = max(HORIZONS_MIN)
    window = bars_1m[entry_idx : entry_idx + horizon_max]
    for h in HORIZONS_MIN:
        j = entry_idx + h - 1
        if j < len(bars_1m):
            ret = bars_1m[j].close - entry
            fwd[f"ret_{h}"] = round(ret, 2)
            fwd[f"ret_pct_{h}"] = round(100.0 * ret / entry, 2) if entry > 0 else None
        else:
            fwd[f"ret_{h}"] = None
            fwd[f"ret_pct_{h}"] = None
    if window:
        mfe = round(max(b.high for b in window) - entry, 2)
        mae = round(min(b.low for b in window) - entry, 2)
    else:
        mfe = mae = None
    return fwd, mfe, mae


def evaluate_combo(
    bars_1m: list[TapeBar],
    *,
    day: str,
    underlying: str,
    side: str,
    timeframe: int,
    gate: str,
    overlay: str,
) -> list[SignalRecord]:
    """Rising-edge signals for one combination, validated on the 1m series.

    Entry is the NEXT 1m bar open after the signal bar closes — no lookahead.
    """
    tf_bars = resample(bars_1m, timeframe)
    gates = gate_series(tf_bars, gate)
    or_levels = opening_range(bars_1m)
    ts_to_1m = {b.ts: i for i, b in enumerate(bars_1m)}
    records: list[SignalRecord] = []
    for i in range(1, len(tf_bars)):
        if not gates[i] or gates[i - 1]:
            continue  # rising edge only
        bar = tf_bars[i]
        if _minute_of(bar.ts) >= NO_ENTRY_AFTER_MIN:
            continue
        # 1m index of the last 1m bar inside this tf bar:
        close_1m_idx = None
        for k in range(timeframe - 1, -1, -1):
            idx = ts_to_1m.get(bar.ts + k * 60)
            if idx is not None:
                close_1m_idx = idx
                break
        if close_1m_idx is None or close_1m_idx + 1 >= len(bars_1m):
            continue
        if not overlay_ok(overlay, bar, bars_1m[: close_1m_idx + 1], or_levels):
            continue
        entry_idx = close_1m_idx + 1
        entry = bars_1m[entry_idx].open
        if entry <= 0:
            continue
        fwd, mfe, mae = _forward_stats(bars_1m, entry_idx, entry)
        records.append(
            SignalRecord(
                day=day,
                underlying=underlying,
                side=side,
                timeframe=timeframe,
                gate=gate,
                overlay=overlay,
                signal_ts=bar.ts,
                signal_ist=datetime.fromtimestamp(bar.ts, tz=IST).isoformat(timespec="minutes"),
                entry_price=round(entry, 2),
                fwd=fwd,
                mfe_30=mfe,
                mae_30=mae,
                shell_pl_pct=shell_outcome(bars_1m, entry_idx, entry),
            )
        )
    return records


def summarize(records: list[SignalRecord]) -> list[dict[str, Any]]:
    """Aggregate per (timeframe, gate, overlay): counts and forward stats."""
    groups: dict[tuple[int, str, str], list[SignalRecord]] = {}
    for r in records:
        groups.setdefault((r.timeframe, r.gate, r.overlay), []).append(r)
    rows: list[dict[str, Any]] = []
    for (tf, gate, overlay), recs in sorted(groups.items()):
        rets = [r.fwd.get("ret_pct_15") for r in recs if r.fwd.get("ret_pct_15") is not None]
        rets30 = [r.fwd.get("ret_pct_30") for r in recs if r.fwd.get("ret_pct_30") is not None]
        maes = [r.mae_30 for r in recs if r.mae_30 is not None]
        entries = [r.entry_price for r in recs if r.mae_30 is not None]
        mae_pct = (
            round(100.0 * sum(m / e for m, e in zip(maes, entries)) / len(maes), 2)
            if maes and entries
            else None
        )
        shells = [r.shell_pl_pct for r in recs if r.shell_pl_pct is not None]
        rows.append(
            {
                "timeframe": tf,
                "gate": gate,
                "overlay": overlay,
                "signals": len(recs),
                "pos_15m": sum(1 for x in rets if x > 0),
                "avg_ret_pct_15m": round(sum(rets) / len(rets), 2) if rets else None,
                "avg_ret_pct_30m": round(sum(rets30) / len(rets30), 2) if rets30 else None,
                "avg_mae_pct_30m": mae_pct,
                "avg_shell_pl_pct": round(sum(shells) / len(shells), 2) if shells else None,
            }
        )
    return rows
