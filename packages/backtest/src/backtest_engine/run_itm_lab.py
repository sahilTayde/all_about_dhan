"""PhD-style ITM option premium lab: EDA + multi-MIX grids on Aug–Sep tape.

PAPER / research only. NO_PROMOTE. No live orders. No STRAT-015+.
Uses Dhan OHLC+volume+OI only; indicators computed client-side.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from dhan_client.client import DhanClient
from dhan_client.config import load_settings, repo_root

from backtest_engine.clocks import session_date_ist
from backtest_engine.costs import apply_round_trip
from backtest_engine.fetch import fetch_chunk
from backtest_engine.indicators import Bar, ema, macd_hist, rsi, session_vwap_of, sma, wma
from backtest_engine.simulate import Trade

IST = timezone(timedelta(hours=5, minutes=30))
LOT = 65
MIX_PREFIX = "MIX-ITM-LAB"


def _log(msg: str) -> None:
    print(f"[itm-lab] {msg}", file=sys.stderr, flush=True)


def bollinger(
    closes: list[float], length: int = 20, mult: float = 2.0
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    mid = sma(closes, length)
    upper: list[float | None] = []
    lower: list[float | None] = []
    for i in range(len(closes)):
        if mid[i] is None:
            upper.append(None)
            lower.append(None)
            continue
        window = closes[i + 1 - length : i + 1]
        mean = mid[i]
        var = sum((x - mean) ** 2 for x in window) / length
        sd = math.sqrt(var)
        upper.append(mean + mult * sd)
        lower.append(mean - mult * sd)
    return lower, mid, upper


def load_opt(
    client: DhanClient, sid: str, start: datetime, end: datetime
) -> list[Bar]:
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
        raise RuntimeError(f"fetch {sid}: {err}")
    return bars


def align_pair(pe: list[Bar], ce: list[Bar]) -> tuple[list[Bar], list[Bar]]:
    pe_m = {b.ts: b for b in pe}
    ce_m = {b.ts: b for b in ce}
    ts = sorted(set(pe_m) & set(ce_m))
    return [pe_m[t] for t in ts], [ce_m[t] for t in ts]


def eda(pe: list[Bar], ce: list[Bar]) -> dict[str, Any]:
    closes = [b.close for b in pe]
    rets = [(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes)) if closes[i - 1] > 0]
    vols = [b.volume for b in pe]
    pe_a, ce_a = align_pair(pe, ce)
    pe_c = [b.close for b in pe_a]
    ce_c = [b.close for b in ce_a]
    # Pearson PE vs CE returns
    if len(pe_c) > 2:
        pr = [(pe_c[i] / pe_c[i - 1] - 1) for i in range(1, len(pe_c)) if pe_c[i - 1] > 0]
        cr = [(ce_c[i] / ce_c[i - 1] - 1) for i in range(1, len(ce_c)) if ce_c[i - 1] > 0]
        n = min(len(pr), len(cr))
        pr, cr = pr[:n], cr[:n]
        mp, mc = sum(pr) / n, sum(cr) / n
        cov = sum((a - mp) * (b - mc) for a, b in zip(pr, cr)) / n
        sp = math.sqrt(sum((a - mp) ** 2 for a in pr) / n) or 1e-12
        sc = math.sqrt(sum((b - mc) ** 2 for b in cr) / n) or 1e-12
        corr = cov / (sp * sc)
    else:
        corr = None
    # Session S/R: session high/low of PE premium
    by_day: dict[str, list[Bar]] = {}
    for b in pe:
        by_day.setdefault(session_date_ist(b.ts), []).append(b)
    sessions = []
    for day, bars in sorted(by_day.items()):
        sessions.append(
            {
                "day": day,
                "open": bars[0].open,
                "high": max(x.high for x in bars),
                "low": min(x.low for x in bars),
                "close": bars[-1].close,
                "range": max(x.high for x in bars) - min(x.low for x in bars),
                "volume": sum(x.volume for x in bars),
                "bars": len(bars),
            }
        )
    mean_r = sum(rets) / len(rets) if rets else 0.0
    var_r = sum((r - mean_r) ** 2 for r in rets) / len(rets) if rets else 0.0
    # Autocorr lag-1
    if len(rets) > 2:
        m = sum(rets) / len(rets)
        num = sum((rets[i] - m) * (rets[i - 1] - m) for i in range(1, len(rets)))
        den = sum((r - m) ** 2 for r in rets) or 1e-12
        ac1 = num / den
    else:
        ac1 = None
    return {
        "pe_bars": len(pe),
        "ce_aligned_bars": len(pe_a),
        "pe_close_first": pe[0].close if pe else None,
        "pe_close_last": pe[-1].close if pe else None,
        "pe_return_pct": round((pe[-1].close / pe[0].close - 1) * 100, 2) if pe and pe[0].close else None,
        "ce_return_pct": round((ce[-1].close / ce[0].close - 1) * 100, 2) if ce and ce[0].close else None,
        "mean_1m_return": mean_r,
        "std_1m_return": math.sqrt(var_r),
        "autocorr_lag1": ac1,
        "pe_ce_return_corr": corr,
        "volume_zero_frac": (sum(1 for v in vols if v <= 0) / len(vols)) if vols else None,
        "volume_mean": (sum(vols) / len(vols)) if vols else None,
        "volume_p90": sorted(vols)[int(0.9 * (len(vols) - 1))] if vols else None,
        "sessions": sessions,
        "note": (
            "PE vs CE same-strike 1m return correlation expected negative "
            "(inverse premium moves). Autocorr tests momentum vs mean-revert."
        ),
    }


SignalFn = Callable[[list[Bar], list[Bar]], tuple[list[bool], list[bool]]]


def _sim(
    bars: list[Bar],
    entry: list[bool],
    exit_: list[bool],
    *,
    side: str,
    strategy_id: str,
    sl: Optional[float] = None,
    tp: Optional[float] = None,
    fill_next_open: bool = True,
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
                if fill_next_open and i + 1 < len(bars):
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
            if fill_next_open:
                if i + 1 >= len(bars):
                    break
                entry_ts, entry_px = bars[i + 1].ts, bars[i + 1].open
            else:
                entry_ts, entry_px = bar.ts, bar.close
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
            "avg_trade_inr": None,
            "max_dd_inr": 0.0,
        }
    costed = [apply_round_trip(t) for t in trades]
    gross = sum(t.points for t in trades) * LOT
    after = sum(t.points for t in costed) * LOT
    wins = sum(1 for t in trades if t.points > 0)
    # equity curve drawdown
    eq = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        eq += t.points * LOT
        peak = max(peak, eq)
        max_dd = min(max_dd, eq - peak)
    return {
        "trade_count": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate": wins / len(trades),
        "gross_pnl_inr": round(gross, 2),
        "after_cost_pnl_inr": round(after, 2),
        "avg_trade_inr": round(gross / len(trades), 2),
        "max_dd_inr": round(max_dd, 2),
    }


def strat_vwap_rsi_cross(
    pe: list[Bar], ce: list[Bar], *, rsi_en=70.0, rsi_ex=68.0, use_ce_filter=False
) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in pe]
    rv, ef, ws, eb = rsi(c, 14), ema(c, 3), wma(c, 21), ema(c, 21)
    vw = session_vwap_of(pe, c, equal_weight_if_no_volume=True)
    ce_c = {b.ts: b.close for b in ce}
    entry = [False] * len(pe)
    exit_ = [False] * len(pe)
    for i in range(1, len(pe)):
        if None in (rv[i], ef[i], ws[i], eb[i], vw[i], ef[i - 1], ws[i - 1]):
            continue
        cross_up = ef[i - 1] <= ws[i - 1] and ef[i] > ws[i]
        cross_dn = ef[i - 1] >= ws[i - 1] and ef[i] < ws[i]
        ok = c[i] > vw[i] and rv[i] >= rsi_en and c[i] > eb[i] and cross_up
        if use_ce_filter:
            # inverse: CE not making new strength — CE 1m return <= 0
            prev = ce_c.get(pe[i - 1].ts)
            cur = ce_c.get(pe[i].ts)
            if prev and cur and cur > prev:
                ok = False
        entry[i] = ok
        exit_[i] = cross_dn or rv[i] < rsi_ex
    return entry, exit_


def strat_vwap_rsi_state(
    pe: list[Bar], ce: list[Bar], *, rsi_en=70.0, rsi_ex=68.0
) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in pe]
    rv, ef, ws, eb = rsi(c, 14), ema(c, 3), wma(c, 21), ema(c, 21)
    vw = session_vwap_of(pe, c, equal_weight_if_no_volume=True)
    setup = [False] * len(pe)
    exit_ = [False] * len(pe)
    for i in range(1, len(pe)):
        if None in (rv[i], ef[i], ws[i], eb[i], vw[i], ef[i - 1], ws[i - 1]):
            continue
        setup[i] = c[i] > vw[i] and rv[i] >= rsi_en and c[i] > eb[i] and ef[i] > ws[i]
        exit_[i] = (ef[i - 1] >= ws[i - 1] and ef[i] < ws[i]) or rv[i] < rsi_ex
    rising = [setup[i] and not (setup[i - 1] if i else False) for i in range(len(pe))]
    return rising, exit_


def strat_ema_stack(
    pe: list[Bar], ce: list[Bar], *, rsi_en=55.0, rsi_ex=50.0
) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in pe]
    e5, e9, e15, e21 = ema(c, 5), ema(c, 9), ema(c, 15), ema(c, 21)
    rv = rsi(c, 14)
    setup = [False] * len(pe)
    exit_ = [False] * len(pe)
    for i in range(len(pe)):
        if None in (e5[i], e9[i], e15[i], e21[i], rv[i]):
            continue
        bull = e5[i] > e9[i] > e15[i] > e21[i] and c[i] > e21[i] and rv[i] >= rsi_en
        setup[i] = bull
        exit_[i] = e5[i] < e9[i] or rv[i] < rsi_ex
    rising = [setup[i] and not (setup[i - 1] if i else False) for i in range(len(pe))]
    return rising, exit_


def strat_bb_meanrev(
    pe: list[Bar], ce: list[Bar], *, length=20, mult=2.0, rsi_en=35.0, rsi_ex=55.0
) -> tuple[list[bool], list[bool]]:
    """Long premium when washed out to lower band (mean-revert up in premium)."""
    c = [b.close for b in pe]
    lo, mid, up = bollinger(c, length, mult)
    rv = rsi(c, 14)
    entry = [False] * len(pe)
    exit_ = [False] * len(pe)
    for i in range(1, len(pe)):
        if None in (lo[i], mid[i], rv[i], lo[i - 1]):
            continue
        # reclaim lower band
        entry[i] = c[i - 1] <= lo[i - 1] and c[i] > lo[i] and rv[i] <= rsi_en + 15
        exit_[i] = (mid[i] is not None and c[i] >= mid[i]) or rv[i] >= rsi_ex
    return entry, exit_


def strat_macd_hist(pe: list[Bar], ce: list[Bar]) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in pe]
    h = macd_hist(c)
    vw = session_vwap_of(pe, c, equal_weight_if_no_volume=True)
    entry = [False] * len(pe)
    exit_ = [False] * len(pe)
    for i in range(1, len(pe)):
        if h[i] is None or h[i - 1] is None or vw[i] is None:
            continue
        entry[i] = h[i - 1] <= 0 and h[i] > 0 and c[i] > vw[i]
        exit_[i] = h[i - 1] >= 0 and h[i] < 0
    return entry, exit_


def strat_vwap_volume(
    pe: list[Bar], ce: list[Bar], *, vol_mult=1.5, rsi_en=55.0, rsi_ex=50.0
) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in pe]
    v = [b.volume for b in pe]
    vw = session_vwap_of(pe, c, equal_weight_if_no_volume=True)
    vs = sma(v, 20)
    rv = rsi(c, 14)
    e9, e21 = ema(c, 9), ema(c, 21)
    setup = [False] * len(pe)
    exit_ = [False] * len(pe)
    for i in range(len(pe)):
        if None in (vw[i], vs[i], rv[i], e9[i], e21[i]):
            continue
        setup[i] = (
            c[i] > vw[i]
            and v[i] >= vol_mult * vs[i]
            and rv[i] >= rsi_en
            and e9[i] > e21[i]
        )
        exit_[i] = c[i] < vw[i] or rv[i] < rsi_ex or e9[i] < e21[i]
    rising = [setup[i] and not (setup[i - 1] if i else False) for i in range(len(pe))]
    return rising, exit_


def strat_session_sr(
    pe: list[Bar], ce: list[Bar], *, rsi_en=50.0
) -> tuple[list[bool], list[bool]]:
    """Buy bounce off session VWAP from below with RSI reclaim (S/R proxy)."""
    c = [b.close for b in pe]
    vw = session_vwap_of(pe, c, equal_weight_if_no_volume=True)
    rv = rsi(c, 14)
    entry = [False] * len(pe)
    exit_ = [False] * len(pe)
    for i in range(1, len(pe)):
        if None in (vw[i], vw[i - 1], rv[i], rv[i - 1]):
            continue
        entry[i] = c[i - 1] < vw[i - 1] and c[i] >= vw[i] and rv[i] >= rsi_en
        exit_[i] = c[i] < vw[i] or rv[i] < rsi_en - 5
    return entry, exit_


def run_lab() -> dict[str, Any]:
    client = DhanClient(load_settings())
    start = datetime(2026, 8, 1, 9, 15, tzinfo=IST)
    end = datetime(2026, 9, 12, 15, 30, tzinfo=IST)
    _log("load PE 47298 + CE 47297 (same strike 23500)")
    pe = load_opt(client, "47298", start, end)
    ce = load_opt(client, "47297", start, end)
    stats = eda(pe, ce)

    grids: list[dict[str, Any]] = []

    def run_one(name: str, entry: list[bool], exit_: list[bool], params: dict[str, Any]) -> None:
        trades = _sim(
            pe,
            entry,
            exit_,
            side="PE",
            strategy_id=name,
            sl=params.get("sl"),
            tp=params.get("tp"),
        )
        grids.append({"mix_id": name, "params": params, **score(trades)})

    for rsi_en, rsi_ex in [(70, 68), (65, 60), (60, 55)]:
        for sl, tp in [(None, None), (0.15, 0.30), (0.10, 0.20), (0.20, 0.40)]:
            e, x = strat_vwap_rsi_cross(pe, ce, rsi_en=rsi_en, rsi_ex=rsi_ex)
            run_one(
                f"{MIX_PREFIX}-VWAP-RSI-CROSS",
                e,
                x,
                {"rsi_en": rsi_en, "rsi_ex": rsi_ex, "sl": sl, "tp": tp, "family": "cross"},
            )
            e, x = strat_vwap_rsi_state(pe, ce, rsi_en=rsi_en, rsi_ex=rsi_ex)
            run_one(
                f"{MIX_PREFIX}-VWAP-RSI-STATE",
                e,
                x,
                {"rsi_en": rsi_en, "rsi_ex": rsi_ex, "sl": sl, "tp": tp, "family": "state"},
            )
            e, x = strat_vwap_rsi_cross(
                pe, ce, rsi_en=rsi_en, rsi_ex=rsi_ex, use_ce_filter=True
            )
            run_one(
                f"{MIX_PREFIX}-VWAP-RSI-CROSS-CEFILT",
                e,
                x,
                {
                    "rsi_en": rsi_en,
                    "rsi_ex": rsi_ex,
                    "sl": sl,
                    "tp": tp,
                    "family": "cross_cefilt",
                },
            )

    for rsi_en, rsi_ex in [(55, 50), (60, 55), (50, 45)]:
        for sl, tp in [(None, None), (0.15, 0.30)]:
            e, x = strat_ema_stack(pe, ce, rsi_en=rsi_en, rsi_ex=rsi_ex)
            run_one(
                f"{MIX_PREFIX}-EMA-STACK",
                e,
                x,
                {"rsi_en": rsi_en, "rsi_ex": rsi_ex, "sl": sl, "tp": tp, "family": "ema_stack"},
            )

    for length, mult in [(20, 2.0), (20, 2.5), (14, 2.0)]:
        for sl, tp in [(None, None), (0.15, 0.30)]:
            e, x = strat_bb_meanrev(pe, ce, length=length, mult=mult)
            run_one(
                f"{MIX_PREFIX}-BB-MEANREV",
                e,
                x,
                {"length": length, "mult": mult, "sl": sl, "tp": tp, "family": "bb"},
            )

    for sl, tp in [(None, None), (0.15, 0.30)]:
        e, x = strat_macd_hist(pe, ce)
        run_one(
            f"{MIX_PREFIX}-MACD-VWAP",
            e,
            x,
            {"sl": sl, "tp": tp, "family": "macd"},
        )

    for vol_mult in [1.5, 2.0, 2.5]:
        for rsi_en in [50, 55, 60]:
            for sl, tp in [(None, None), (0.15, 0.30)]:
                e, x = strat_vwap_volume(pe, ce, vol_mult=vol_mult, rsi_en=rsi_en)
                run_one(
                    f"{MIX_PREFIX}-VWAP-VOL",
                    e,
                    x,
                    {
                        "vol_mult": vol_mult,
                        "rsi_en": rsi_en,
                        "sl": sl,
                        "tp": tp,
                        "family": "vol",
                    },
                )

    for rsi_en in [45, 50, 55]:
        for sl, tp in [(None, None), (0.15, 0.30)]:
            e, x = strat_session_sr(pe, ce, rsi_en=rsi_en)
            run_one(
                f"{MIX_PREFIX}-SR-VWAP",
                e,
                x,
                {"rsi_en": rsi_en, "sl": sl, "tp": tp, "family": "sr"},
            )

    # Rank: prefer after-cost, then trade_count>=5, then lower drawdown
    ranked = sorted(
        grids,
        key=lambda r: (
            r["after_cost_pnl_inr"],
            r["gross_pnl_inr"],
            r["trade_count"],
            -abs(r["max_dd_inr"]),
        ),
        reverse=True,
    )
    # Best per family
    best_family: dict[str, dict[str, Any]] = {}
    for row in ranked:
        fam = row["params"].get("family", "?")
        if fam not in best_family:
            best_family[fam] = row

    report = {
        "title": "ITM option premium lab — NIFTY 23500 PE vs 23500 CE",
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "contracts": {
            "PE": {"security_id": "47298", "strike": 23500, "lot": LOT},
            "CE": {"security_id": "47297", "strike": 23500, "lot": LOT},
        },
        "promotion": "NO_PROMOTE",
        "orders": "refused",
        "verdict": "UNVALIDATED",
        "live_auto_trade": "REFUSED — paper/shadow signals only until gate",
        "eda": stats,
        "grid_size": len(grids),
        "top_20": ranked[:20],
        "best_per_family": best_family,
        "bottom_5": ranked[-5:],
        "honesty": [
            "PAPER only. Not a customer promote. Not live Super Order automation.",
            "Indicators computed from Dhan OHLC+volume; not chart panes.",
            "After-cost uses HYPOTHESIS 1% RT slip; statutory UNKNOWN.",
            "Aug–Sep only = small sample; multiple-testing bias high across grid.",
            "KEEP_ALL: lab MIX-* does not replace STRAT-001–014.",
        ],
    }

    out = repo_root() / "data" / "recon" / "itm_lab_aug_sep.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    mock = repo_root() / "apps" / "web" / "public" / "mock" / "itm_lab_aug_sep.json"
    mock.parent.mkdir(parents=True, exist_ok=True)
    mock.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _log(f"wrote {out}")
    return report


def counsel_lab(report: dict[str, Any]) -> dict[str, Any]:
    """Ask Gemini + OpenAI to critique EDA + top families (keys from env)."""
    from trading_agents_india.counsel import (
        _complete_gemini,
        _complete_openai,
        counsel_settings,
    )

    cfg = counsel_settings()
    compact = {
        "eda": {
            k: report["eda"][k]
            for k in (
                "pe_bars",
                "pe_return_pct",
                "ce_return_pct",
                "pe_ce_return_corr",
                "autocorr_lag1",
                "std_1m_return",
                "volume_zero_frac",
            )
            if k in report["eda"]
        },
        "best_per_family": {
            k: {
                "after_cost_pnl_inr": v["after_cost_pnl_inr"],
                "gross_pnl_inr": v["gross_pnl_inr"],
                "trade_count": v["trade_count"],
                "win_rate": v["win_rate"],
                "params": v["params"],
            }
            for k, v in (report.get("best_per_family") or {}).items()
        },
        "top_5": report.get("top_20", [])[:5],
    }
    prompt = (
        "You are a PhD statistician reviewing an OPTIONS PREMIUM 1m backtest lab "
        "(NIFTY 23500 PE Aug–Sep 2026). PAPER only. No live orders.\n"
        "Facts JSON:\n"
        f"{json.dumps(compact)}\n\n"
        "Reply with:\n"
        "1) AGREE / DISAGREE that PE-CE return corr and autocorr imply mean-revert vs momentum.\n"
        "2) Which family looks least overfit given small sample + large grid.\n"
        "3) What MUST NOT be claimed (multiple testing, short window).\n"
        "4) One next BACKTEST_REQUIRED experiment (single hypothesis).\n"
        "Be blunt. No invented win rates beyond the JSON."
    )
    out: dict[str, Any] = {
        "settings": {
            k: v
            for k, v in cfg.items()
            if "key" in k or k.endswith("model") or k == "provider"
        }
    }
    if not (cfg.get("gemini_key_present") or cfg.get("openai_key_present")):
        out["ok"] = False
        out["gap"] = "DATA_INSUFFICIENT: no GEMINI/OPENAI keys for counsel"
        return out
    g = (
        _complete_gemini(prompt, cfg["gemini_model"])
        if cfg["gemini_key_present"]
        else {"ok": False, "gap": "gemini_missing"}
    )
    o = (
        _complete_openai(prompt, cfg["openai_model"])
        if cfg["openai_key_present"]
        else {"ok": False, "gap": "openai_missing"}
    )
    out["ok"] = bool(g.get("ok") or o.get("ok"))
    out["gemini"] = g
    out["openai"] = o
    return out


if __name__ == "__main__":
    rep = run_lab()
    counsel = counsel_lab(rep)
    rep["counsel"] = counsel
    path = repo_root() / "data" / "recon" / "itm_lab_aug_sep.json"
    path.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    # print slim stdout
    slim = {
        "eda_highlights": {
            k: rep["eda"][k]
            for k in (
                "pe_bars",
                "pe_return_pct",
                "ce_return_pct",
                "pe_ce_return_corr",
                "autocorr_lag1",
                "volume_zero_frac",
            )
        },
        "grid_size": rep["grid_size"],
        "best_per_family": {
            k: {
                "after_cost": v["after_cost_pnl_inr"],
                "gross": v["gross_pnl_inr"],
                "trades": v["trade_count"],
                "wr": v["win_rate"],
                "params": v["params"],
            }
            for k, v in rep["best_per_family"].items()
        },
        "top_5": [
            {
                "mix": r["mix_id"],
                "after_cost": r["after_cost_pnl_inr"],
                "gross": r["gross_pnl_inr"],
                "trades": r["trade_count"],
                "wr": r["win_rate"],
                "params": r["params"],
            }
            for r in rep["top_20"][:5]
        ],
        "counsel_ok": counsel.get("ok"),
        "live_auto_trade": rep["live_auto_trade"],
        "path": str(path),
    }
    print(json.dumps(slim, indent=2, default=str))
