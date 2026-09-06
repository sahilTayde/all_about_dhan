"""Chart Fanatics Fabio OHLC proxies. EXTERNAL guest — not DHAN-DERIVED.

Teacher trigger is order-flow aggression (PARKED). These leans approximate
failed-auction / profile mean-revert / break-retest structure from INDEX OHLC only.
No win-rate claim. No live orders.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from backtest_engine.clocks import session_date_ist
from backtest_engine.indicators import Bar


def _daily_ohlcv(bars: list[Bar]) -> dict[str, tuple[float, float, float, float]]:
    """session -> (high, low, close, volume_sum)."""
    bucket: dict[str, list[Bar]] = defaultdict(list)
    for bar in bars:
        bucket[session_date_ist(bar.ts)].append(bar)
    out: dict[str, tuple[float, float, float, float]] = {}
    for day, rows in bucket.items():
        out[day] = (
            max(b.high for b in rows),
            min(b.low for b in rows),
            rows[-1].close,
            sum(b.volume for b in rows),
        )
    return out


def _prev_map(
    daily: dict[str, tuple[float, float, float, float]],
) -> dict[str, tuple[float, float, float, float]]:
    days = sorted(daily)
    prev: dict[str, tuple[float, float, float, float]] = {}
    for i, day in enumerate(days):
        if i == 0:
            continue
        prev[day] = daily[days[i - 1]]
    return prev


def prior_session_profile(
    bars: list[Bar],
    *,
    bins: int = 24,
    va_frac: float = 0.70,
) -> dict[str, dict[str, float]]:
    """HYPOTHESIS volume profile on prior session bars.

    va_frac=0.70 is classic textbook default — bind did not freeze VA%.
    If session volume is all zero, equal-weight each bar (PROJECT ablation).
    """
    by_day: dict[str, list[Bar]] = defaultdict(list)
    for bar in bars:
        by_day[session_date_ist(bar.ts)].append(bar)
    days = sorted(by_day)
    out: dict[str, dict[str, float]] = {}
    for i, day in enumerate(days):
        if i == 0:
            continue
        prev_day = days[i - 1]
        rows = by_day[prev_day]
        lo = min(b.low for b in rows)
        hi = max(b.high for b in rows)
        if hi <= lo:
            mid = rows[-1].close
            out[day] = {"poc": mid, "val": mid, "vah": mid, "pdh": hi, "pdl": lo, "pdc": rows[-1].close}
            continue
        width = (hi - lo) / bins
        vol = [0.0] * bins
        for b in rows:
            typical = (b.high + b.low + b.close) / 3.0
            w = b.volume if b.volume > 0 else 1.0
            idx = int((typical - lo) / width)
            idx = max(0, min(bins - 1, idx))
            vol[idx] += w
        poc_i = max(range(bins), key=lambda j: vol[j])
        poc = lo + (poc_i + 0.5) * width
        total = sum(vol) or 1.0
        need = total * va_frac
        left = right = poc_i
        got = vol[poc_i]
        while got < need and (left > 0 or right < bins - 1):
            expand_left = vol[left - 1] if left > 0 else -1.0
            expand_right = vol[right + 1] if right < bins - 1 else -1.0
            if expand_left >= expand_right and left > 0:
                left -= 1
                got += vol[left]
            elif right < bins - 1:
                right += 1
                got += vol[right]
            else:
                break
        out[day] = {
            "poc": poc,
            "val": lo + left * width,
            "vah": lo + (right + 1) * width,
            "pdh": hi,
            "pdl": lo,
            "pdc": rows[-1].close,
        }
    return out


def lean_cf_failed_auction(bars: list[Bar], *, confirm_bars: int = 3) -> list[str]:
    """Sweep prior-day high/low then close back inside within confirm_bars.

    SOURCE_FACT language: failed auction / 'people call manipulation'.
    No OF — structure proxy only. CE = failed low auction (sweep low, reclaim).
    PE = failed high auction.
    """
    daily = _daily_ohlcv(bars)
    prev = _prev_map(daily)
    out = ["SKIP"] * len(bars)
    # Track first touch state per session
    state: dict[str, dict[str, Optional[int]]] = {}
    for i, bar in enumerate(bars):
        day = session_date_ist(bar.ts)
        p = prev.get(day)
        if not p:
            continue
        pdh, pdl, _pdc, _v = p
        st = state.setdefault(day, {"hi_i": None, "lo_i": None, "done_hi": False, "done_lo": False})
        if bar.high >= pdh and st["hi_i"] is None:
            st["hi_i"] = i
        if bar.low <= pdl and st["lo_i"] is None:
            st["lo_i"] = i
        if st["hi_i"] is not None and not st["done_hi"]:
            if 0 < i - st["hi_i"] <= confirm_bars and bar.close < pdh:
                out[i] = "PE"
                st["done_hi"] = True
        if st["lo_i"] is not None and not st["done_lo"]:
            if 0 < i - st["lo_i"] <= confirm_bars and bar.close > pdl:
                out[i] = "CE"
                st["done_lo"] = True
    return out


def lean_cf_break_retest_pd(bars: list[Bar], *, retest_bars: int = 8) -> list[str]:
    """Break prior-day range, retest edge, continue (trend-model structure proxy).

    First drive alone is skipped: require break, then touch back to edge, then close beyond again.
    """
    daily = _daily_ohlcv(bars)
    prev = _prev_map(daily)
    out = ["SKIP"] * len(bars)
    st: dict[str, dict] = {}
    for i, bar in enumerate(bars):
        day = session_date_ist(bar.ts)
        p = prev.get(day)
        if not p:
            continue
        pdh, pdl, _c, _v = p
        s = st.setdefault(
            day,
            {"broke_hi": False, "broke_lo": False, "retest_hi": False, "retest_lo": False, "brk_i": None},
        )
        if not s["broke_hi"] and bar.close > pdh:
            s["broke_hi"] = True
            s["brk_i"] = i
            continue
        if not s["broke_lo"] and bar.close < pdl:
            s["broke_lo"] = True
            s["brk_i"] = i
            continue
        if s["broke_hi"] and not s["retest_hi"] and s["brk_i"] is not None:
            if i > s["brk_i"] and bar.low <= pdh:
                s["retest_hi"] = True
                continue
        if s["broke_lo"] and not s["retest_lo"] and s["brk_i"] is not None:
            if i > s["brk_i"] and bar.high >= pdl:
                s["retest_lo"] = True
                continue
        if s["retest_hi"] and bar.close > pdh:
            if s["brk_i"] is not None and i - s["brk_i"] <= retest_bars + 20:
                out[i] = "CE"
                s["retest_hi"] = False  # one-shot per wave
                s["broke_hi"] = False
        if s["retest_lo"] and bar.close < pdl:
            if s["brk_i"] is not None and i - s["brk_i"] <= retest_bars + 20:
                out[i] = "PE"
                s["retest_lo"] = False
                s["broke_lo"] = False
    return out


def lean_cf_mr_to_poc(bars: list[Bar]) -> list[str]:
    """Outside prior VA then close back toward POC (mean-revert model proxy)."""
    profiles = prior_session_profile(bars)
    out: list[str] = []
    for bar in bars:
        day = session_date_ist(bar.ts)
        prof = profiles.get(day)
        if not prof:
            out.append("SKIP")
            continue
        _poc, val, vah = prof["poc"], prof["val"], prof["vah"]
        # Outside VA then reclaim inside (toward balance / POC). Structure proxy only.
        if bar.low < val and bar.close > val:
            out.append("CE")
        elif bar.high > vah and bar.close < vah:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def gap_summary() -> dict[str, str]:
    return {
        "order_flow_bubbles": "DATA_INSUFFICIENT",
        "cvd": "DATA_INSUFFICIENT",
        "footprint": "DATA_INSUFFICIENT",
        "nq_contract_filter": "NOT_MAPPED_TO_NIFTY",
        "ny_london_clocks": "DATA_INSUFFICIENT_FOR_NSE",
        "gex_option_chain": "NOT_IN_RECIPE",
        "teacher_asset": "NQ_FUTURES",
        "proxy_layer": "PROJECT_MIX_OHLC",
    }
