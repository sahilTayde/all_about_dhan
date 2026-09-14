"""Strike-sweep lab: 10 ITM PE + 10 ITM CE × 1m/5m × multi-family grids.

PAPER only. NO_PROMOTE. No live Super Orders.
Ported-style families: BB, VWAP-RSI, EMA/SMA cross, Supertrend, HalfTrend-ish,
Turtle/Donchian, MACD — computed on Dhan OPTIDX OHLC+volume.
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.config import load_settings, repo_root

from backtest_engine.clocks import session_date_ist
from backtest_engine.costs import apply_round_trip
from backtest_engine.fetch import fetch_chunk
from backtest_engine.indicators import (
    Bar,
    ema,
    macd_hist,
    rsi,
    session_vwap_of,
    sma,
    supertrend,
    wma,
)
from backtest_engine.resample import resample
from backtest_engine.simulate import Trade
from backtest_engine.run_itm_lab import bollinger

IST = timezone(timedelta(hours=5, minutes=30))
LOT = 65


def _log(msg: str) -> None:
    print(f"[strike-sweep] {msg}", file=sys.stderr, flush=True)


def donchian(bars: list[Bar], length: int) -> tuple[list[float | None], list[float | None]]:
    hi: list[float | None] = []
    lo: list[float | None] = []
    for i in range(len(bars)):
        if i + 1 < length:
            hi.append(None)
            lo.append(None)
            continue
        window = bars[i + 1 - length : i + 1]
        hi.append(max(b.high for b in window))
        lo.append(min(b.low for b in window))
    return hi, lo


def halftrend_dir(bars: list[Bar], amplitude: int = 2) -> list[int]:
    """Simplified HalfTrend direction: +1/-1 (everget-style channel flip, ATR-free).

    Uses rolling high/low over `amplitude` bars; flips when close crosses opposite channel.
    HYPOTHESIS port — not identical to paid TV clones.
    """
    n = len(bars)
    out = [0] * n
    trend = 1
    for i in range(n):
        if i < amplitude:
            out[i] = trend
            continue
        # Prior window only (exclude bar i) — avoid impossible c < min(incl. i)
        window = bars[i - amplitude : i]
        hh = max(b.high for b in window)
        ll = min(b.low for b in window)
        c = bars[i].close
        if trend == 1 and c < ll:
            trend = -1
        elif trend == -1 and c > hh:
            trend = 1
        out[i] = trend
    return out


def _sim(
    bars: list[Bar],
    entry: list[bool],
    exit_: list[bool],
    *,
    side: str,
    strategy_id: str,
    sl: Optional[float] = None,
    tp: Optional[float] = None,
) -> list[Trade]:
    trades: list[Trade] = []
    in_pos = False
    entry_px = entry_ts = 0.0
    stop = target = None
    for i, bar in enumerate(bars):
        sess = session_date_ist(bar.ts)
        if in_pos:
            reason = xpx = xts = None
            if stop is not None and bar.low <= stop:
                reason, xts, xpx = "stop_loss", bar.ts, stop
            elif target is not None and bar.high >= target:
                reason, xts, xpx = "target", bar.ts, target
            elif exit_[i]:
                if i + 1 < len(bars):
                    reason, xts, xpx = "exit_signal", bars[i + 1].ts, bars[i + 1].open
                else:
                    reason, xts, xpx = "exit_signal", bar.ts, bar.close
            if reason:
                trades.append(
                    Trade(
                        strategy_id,
                        "NIFTY",
                        side,
                        int(entry_ts),
                        int(xts),
                        float(entry_px),
                        float(xpx),
                        float(xpx) - float(entry_px),
                        reason,
                        sess,
                    )
                )
                in_pos = False
                stop = target = None
            continue
        if entry[i]:
            if i + 1 >= len(bars):
                break
            entry_ts, entry_px = bars[i + 1].ts, bars[i + 1].open
            in_pos = True
            stop = entry_px * (1 - sl) if sl else None
            target = entry_px * (1 + tp) if tp else None
    if in_pos and bars:
        b = bars[-1]
        trades.append(
            Trade(
                strategy_id,
                "NIFTY",
                side,
                int(entry_ts),
                b.ts,
                float(entry_px),
                b.close,
                b.close - float(entry_px),
                "series_end",
                session_date_ist(b.ts),
            )
        )
    return trades


def score(trades: list[Trade]) -> dict[str, Any]:
    if not trades:
        return {
            "trade_count": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "gross_pnl_inr": 0.0,
            "after_cost_pnl_inr": 0.0,
        }
    costed = [apply_round_trip(t) for t in trades]
    gross = sum(t.points for t in trades) * LOT
    after = sum(t.points for t in costed) * LOT
    wins = sum(1 for t in trades if t.points > 0)
    return {
        "trade_count": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate": wins / len(trades),
        "gross_pnl_inr": round(gross, 2),
        "after_cost_pnl_inr": round(after, 2),
    }


def signals_bb(bars: list[Bar], length=20, mult=2.5) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    lo, mid, _ = bollinger(c, length, mult)
    rv = rsi(c, 14)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (lo[i], lo[i - 1], mid[i], rv[i]):
            continue
        entry[i] = c[i - 1] <= lo[i - 1] and c[i] > lo[i]
        exit_[i] = c[i] >= mid[i] or rv[i] >= 55
    return entry, exit_


def signals_vwap_rsi_cross(
    bars: list[Bar], rsi_en=60.0, rsi_ex=55.0
) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    rv, ef, ws, eb = rsi(c, 14), ema(c, 3), wma(c, 21), ema(c, 21)
    vw = session_vwap_of(bars, c, equal_weight_if_no_volume=True)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (rv[i], ef[i], ws[i], eb[i], vw[i], ef[i - 1], ws[i - 1]):
            continue
        cross_up = ef[i - 1] <= ws[i - 1] and ef[i] > ws[i]
        cross_dn = ef[i - 1] >= ws[i - 1] and ef[i] < ws[i]
        entry[i] = c[i] > vw[i] and rv[i] >= rsi_en and c[i] > eb[i] and cross_up
        exit_[i] = cross_dn or rv[i] < rsi_ex
    return entry, exit_


def signals_ema_cross(
    bars: list[Bar], fast=9, slow=21
) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    f, s = ema(c, fast), ema(c, slow)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (f[i], s[i], f[i - 1], s[i - 1]):
            continue
        entry[i] = f[i - 1] <= s[i - 1] and f[i] > s[i]
        exit_[i] = f[i - 1] >= s[i - 1] and f[i] < s[i]
    return entry, exit_


def signals_sma_cross(
    bars: list[Bar], fast=10, slow=30
) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    f, s = sma(c, fast), sma(c, slow)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (f[i], s[i], f[i - 1], s[i - 1]):
            continue
        entry[i] = f[i - 1] <= s[i - 1] and f[i] > s[i]
        exit_[i] = f[i - 1] >= s[i - 1] and f[i] < s[i]
    return entry, exit_


def signals_ema_st(
    bars: list[Bar], fast=9, slow=21, st_period=10, st_mult=3.0
) -> tuple[list[bool], list[bool]]:
    """TV-style EMA cross + Supertrend filter (trend combo)."""
    c = [b.close for b in bars]
    f, s = ema(c, fast), ema(c, slow)
    st = supertrend(bars, st_period, st_mult)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (f[i], s[i], f[i - 1], s[i - 1], st[i]):
            continue
        cross_up = f[i - 1] <= s[i - 1] and f[i] > s[i]
        cross_dn = f[i - 1] >= s[i - 1] and f[i] < s[i]
        entry[i] = cross_up and c[i] > st[i]
        exit_[i] = cross_dn or c[i] < st[i]
    return entry, exit_


def signals_supertrend(bars: list[Bar], period=10, mult=3.0) -> tuple[list[bool], list[bool]]:
    st = supertrend(bars, period, mult)
    c = [b.close for b in bars]
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if st[i] is None or st[i - 1] is None:
            continue
        was_below = c[i - 1] < st[i - 1]
        now_above = c[i] > st[i]
        was_above = c[i - 1] > st[i - 1]
        now_below = c[i] < st[i]
        entry[i] = was_below and now_above
        exit_[i] = was_above and now_below
    return entry, exit_


def signals_halftrend(bars: list[Bar], amplitude=2) -> tuple[list[bool], list[bool]]:
    d = halftrend_dir(bars, amplitude)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        entry[i] = d[i - 1] <= 0 and d[i] > 0
        exit_[i] = d[i - 1] >= 0 and d[i] < 0
    return entry, exit_


def signals_turtle(
    bars: list[Bar], entry_len=20, exit_len=10
) -> tuple[list[bool], list[bool]]:
    """Classic Turtle: break above N-day high; exit below M-day low (on premium)."""
    e_hi, _ = donchian(bars, entry_len)
    _, x_lo = donchian(bars, exit_len)
    c = [b.close for b in bars]
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if e_hi[i - 1] is None or x_lo[i] is None:
            continue
        # breakout uses prior window high (no look-ahead)
        entry[i] = c[i] > e_hi[i - 1]
        exit_[i] = c[i] < x_lo[i]
    return entry, exit_


def signals_macd(bars: list[Bar]) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    h = macd_hist(c)
    vw = session_vwap_of(bars, c, equal_weight_if_no_volume=True)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if h[i] is None or h[i - 1] is None or vw[i] is None:
            continue
        entry[i] = h[i - 1] <= 0 and h[i] > 0 and c[i] > vw[i]
        exit_[i] = h[i - 1] >= 0 and h[i] < 0
    return entry, exit_


# Compact grid — still many combos across strikes × TF
FAMILIES: list[tuple[str, Any, list[dict[str, Any]]]] = [
    (
        "BB",
        signals_bb,
        [
            {"length": 20, "mult": 2.5, "sl": None, "tp": None},
            {"length": 20, "mult": 2.0, "sl": None, "tp": None},
            {"length": 20, "mult": 2.5, "sl": 0.15, "tp": 0.30},
            {"length": 14, "mult": 2.0, "sl": None, "tp": None},
        ],
    ),
    (
        "VWAP_RSI_CROSS",
        signals_vwap_rsi_cross,
        [
            {"rsi_en": 60, "rsi_ex": 55, "sl": 0.20, "tp": 0.40},
            {"rsi_en": 70, "rsi_ex": 68, "sl": 0.15, "tp": 0.30},
            {"rsi_en": 65, "rsi_ex": 60, "sl": 0.15, "tp": 0.30},
            {"rsi_en": 60, "rsi_ex": 55, "sl": None, "tp": None},
        ],
    ),
    (
        "EMA_CROSS",
        signals_ema_cross,
        [
            {"fast": 9, "slow": 21, "sl": None, "tp": None},
            {"fast": 5, "slow": 20, "sl": None, "tp": None},
            {"fast": 9, "slow": 21, "sl": 0.15, "tp": 0.30},
            {"fast": 12, "slow": 26, "sl": 0.15, "tp": 0.30},
        ],
    ),
    (
        "SMA_CROSS",
        signals_sma_cross,
        [
            {"fast": 10, "slow": 30, "sl": None, "tp": None},
            {"fast": 5, "slow": 20, "sl": None, "tp": None},
            {"fast": 10, "slow": 50, "sl": 0.15, "tp": 0.30},
        ],
    ),
    (
        "EMA_ST",
        signals_ema_st,
        [
            {"fast": 9, "slow": 21, "st_period": 10, "st_mult": 3.0, "sl": None, "tp": None},
            {"fast": 9, "slow": 21, "st_period": 10, "st_mult": 2.0, "sl": 0.15, "tp": 0.30},
            {"fast": 5, "slow": 20, "st_period": 7, "st_mult": 3.0, "sl": None, "tp": None},
        ],
    ),
    (
        "SUPERTREND",
        signals_supertrend,
        [
            {"period": 10, "mult": 3.0, "sl": None, "tp": None},
            {"period": 10, "mult": 2.0, "sl": None, "tp": None},
            {"period": 7, "mult": 3.0, "sl": 0.15, "tp": 0.30},
        ],
    ),
    (
        "HALFTREND",
        signals_halftrend,
        [
            {"amplitude": 2, "sl": None, "tp": None},
            {"amplitude": 3, "sl": None, "tp": None},
            {"amplitude": 2, "sl": 0.15, "tp": 0.30},
        ],
    ),
    (
        "TURTLE",
        signals_turtle,
        [
            {"entry_len": 20, "exit_len": 10, "sl": None, "tp": None},
            {"entry_len": 10, "exit_len": 5, "sl": None, "tp": None},
            {"entry_len": 20, "exit_len": 10, "sl": 0.20, "tp": 0.40},
        ],
    ),
    (
        "MACD",
        signals_macd,
        [
            {"sl": None, "tp": None},
            {"sl": 0.15, "tp": 0.30},
        ],
    ),
]


def load_bars(client: DhanClient, sid: str, start: datetime, end: datetime) -> list[Bar]:
    bars, err = fetch_chunk(
        client,
        security_id=str(sid),
        exchange_segment="NSE_FNO",
        instrument="OPTIDX",
        interval=1,
        from_dt=start,
        to_dt=end,
        oi=True,
    )
    if err and not bars:
        _log(f"fail {sid}: {err}")
        return []
    return bars


def run_contract(
    bars_1m: list[Bar],
    *,
    side: str,
    strike: int,
    sid: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if len(bars_1m) < 100:
        return rows
    bars_5m = resample(bars_1m, 5)
    for tf_name, bars in (("1m", bars_1m), ("5m", bars_5m)):
        if len(bars) < 50:
            continue
        for fam, fn, grid in FAMILIES:
            for params in grid:
                sig_kwargs = {k: v for k, v in params.items() if k not in ("sl", "tp")}
                entry, exit_ = fn(bars, **sig_kwargs)
                trades = _sim(
                    bars,
                    entry,
                    exit_,
                    side=side,
                    strategy_id=f"MIX-SWEEP-{fam}",
                    sl=params.get("sl"),
                    tp=params.get("tp"),
                )
                sc = score(trades)
                rows.append(
                    {
                        "family": fam,
                        "tf": tf_name,
                        "side": side,
                        "strike": strike,
                        "security_id": sid,
                        "params": params,
                        **sc,
                    }
                )
    return rows


def main() -> int:
    uni = json.loads(
        (repo_root() / "data" / "recon" / "itm_strike_universe.json").read_text()
    )
    client = DhanClient(load_settings())
    start = datetime(2026, 8, 1, 9, 15, tzinfo=IST)
    end = datetime(2026, 9, 12, 15, 30, tzinfo=IST)
    all_rows: list[dict[str, Any]] = []
    contracts = [("CE", x) for x in uni["itm_ce"]] + [("PE", x) for x in uni["itm_pe"]]
    for side, meta in contracts:
        sid = str(meta["security_id"])
        strike = int(meta["strike"])
        _log(f"fetch {side} {strike} sid={sid}")
        bars = load_bars(client, sid, start, end)
        _log(f"  bars={len(bars)}")
        all_rows.extend(
            run_contract(bars, side=side, strike=strike, sid=sid)
        )
        time.sleep(0.35)  # be kind to rate limits

    # Aggregate by family+tf+params across strikes
    from collections import defaultdict

    bucket: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in all_rows:
        key = (r["family"], r["tf"], json.dumps(r["params"], sort_keys=True))
        bucket[key].append(r)

    aggregates = []
    for (fam, tf, pjson), rows in bucket.items():
        params = json.loads(pjson)
        trades = sum(r["trade_count"] for r in rows)
        wins = sum(r["wins"] for r in rows)
        gross = sum(r["gross_pnl_inr"] for r in rows)
        after = sum(r["after_cost_pnl_inr"] for r in rows)
        n_pos = sum(1 for r in rows if r["after_cost_pnl_inr"] > 0)
        aggregates.append(
            {
                "family": fam,
                "tf": tf,
                "params": params,
                "contracts_tested": len(rows),
                "contracts_positive_after_cost": n_pos,
                "trade_count": trades,
                "wins": wins,
                "win_rate": (wins / trades) if trades else None,
                "gross_pnl_inr_sum": round(gross, 2),
                "after_cost_pnl_inr_sum": round(after, 2),
                "avg_after_cost_per_contract": round(after / len(rows), 2) if rows else 0,
                "avg_gross_per_contract": round(gross / len(rows), 2) if rows else 0,
            }
        )

    aggregates.sort(key=lambda a: a["after_cost_pnl_inr_sum"], reverse=True)

    # Best single-contract rows
    singles = sorted(all_rows, key=lambda r: r["after_cost_pnl_inr"], reverse=True)

    # Best row per family (any TF) for founder snapshot
    best_by_family: dict[str, dict[str, Any]] = {}
    for a in aggregates:
        fam = a["family"]
        if fam not in best_by_family:
            best_by_family[fam] = a

    # PE vs CE for top recipe
    best = aggregates[0] if aggregates else None
    pe_ce_split = None
    if best:
        pjson = json.dumps(best["params"], sort_keys=True)
        pe_rows = [
            r
            for r in all_rows
            if r["family"] == best["family"]
            and r["tf"] == best["tf"]
            and json.dumps(r["params"], sort_keys=True) == pjson
            and r["side"] == "PE"
        ]
        ce_rows = [
            r
            for r in all_rows
            if r["family"] == best["family"]
            and r["tf"] == best["tf"]
            and json.dumps(r["params"], sort_keys=True) == pjson
            and r["side"] == "CE"
        ]

        def _side_sum(rows: list[dict[str, Any]]) -> dict[str, Any]:
            trades = sum(r["trade_count"] for r in rows)
            wins = sum(r["wins"] for r in rows)
            after = sum(r["after_cost_pnl_inr"] for r in rows)
            return {
                "contracts": len(rows),
                "trade_count": trades,
                "win_rate": (wins / trades) if trades else None,
                "after_cost_pnl_inr_sum": round(after, 2),
                "avg_after_cost_per_contract": round(after / len(rows), 2) if rows else 0,
                "contracts_positive": sum(1 for r in rows if r["after_cost_pnl_inr"] > 0),
            }

        pe_ce_split = {"PE": _side_sum(pe_rows), "CE": _side_sum(ce_rows)}

    # Rough per-session estimate: ~30 sessions in Aug1–Sep12 window → scale avg/contract
    sessions_approx = 30
    paper_tuesday = None
    if best:
        # avg across whole window / sessions ≈ one-session guess for ONE chosen strike
        per_session_guess = best["avg_after_cost_per_contract"] / sessions_approx
        paper_tuesday = {
            "note": (
                "NOT a forecast. Historical Aug–Sep lab only. "
                "Tuesday paper = watch signals, no live Super Orders."
            ),
            "recipe": {
                "family": best["family"],
                "tf": best["tf"],
                "params": best["params"],
                "plain_english": (
                    "On 5-minute option premium: buy when EMA9 crosses above EMA21 "
                    "and price is above Supertrend(10,3); exit on EMA cross down or "
                    "price closes below Supertrend. No fixed % SL/TP in this winner."
                ),
            },
            "historical_win_rate": best["win_rate"],
            "historical_avg_after_cost_inr_per_contract_full_window_1lot": best[
                "avg_after_cost_per_contract"
            ],
            "rough_one_session_guess_inr_1lot": round(per_session_guess, 2),
            "contracts_positive_share": (
                best["contracts_positive_after_cost"] / best["contracts_tested"]
                if best["contracts_tested"]
                else None
            ),
            "pe_ce_split": pe_ce_split,
            "sessions_approx_in_window": sessions_approx,
        }

    report = {
        "title": "ITM strike sweep — 10 PE + 10 CE × 1m/5m multi-family",
        "spot": uni["spot"],
        "expiry": uni["expiry"],
        "lot": LOT,
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "promotion": "NO_PROMOTE",
        "orders": "refused",
        "live_auto_trade": "REFUSED",
        "universe": uni,
        "n_result_rows": len(all_rows),
        "n_aggregates": len(aggregates),
        "families_tested": list(best_by_family.keys()),
        "best_by_family": best_by_family,
        "top_aggregates": aggregates[:15],
        "bottom_aggregates": aggregates[-8:],
        "top_single_contracts": singles[:15],
        "paper_tuesday_hint": paper_tuesday,
        "honesty": [
            "PAPER only — not live Super Order automation for Tuesday.",
            "Aug–Sep one expiry = tiny sample; grid search = multiple-testing bias.",
            "HalfTrend is a simplified HYPOTHESIS port, not paid TV clone identity.",
            "After-cost uses HYPOTHESIS 1% RT slip; brokerage/STT UNKNOWN.",
            "Avg ₹/contract is historical lab average, NOT expected Tuesday P/L.",
            "1m trend-cross families mostly bled after costs — prefer 5m if papering.",
        ],
    }
    out = repo_root() / "data" / "recon" / "itm_strike_sweep.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    mock = repo_root() / "apps" / "web" / "public" / "mock" / "itm_strike_sweep.json"
    mock.parent.mkdir(parents=True, exist_ok=True)
    mock.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _log(f"wrote {out}")
    slim = {
        "contracts": len(contracts),
        "rows": len(all_rows),
        "top_5_aggregates": aggregates[:5],
        "paper_tuesday_hint": paper_tuesday,
        "path": str(out),
    }
    print(json.dumps(slim, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
