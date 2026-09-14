"""Backtest Flawless Victory on NIFTY ITM option premiums — multi-TF grid.

TFs: 1m, 3m, 5m, 10m, 15m. PAPER only. NO_PROMOTE. No live orders.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.config import load_settings, repo_root

from backtest_engine.clocks import session_date_ist
from backtest_engine.costs import apply_round_trip
from backtest_engine.fetch import fetch_chunk
from backtest_engine.flawless_victory import (
    FlawlessParams,
    default_param_grid,
    flawless_signals,
)
from backtest_engine.indicators import Bar
from backtest_engine.resample import resample
from backtest_engine.simulate import Trade

IST = timezone(timedelta(hours=5, minutes=30))
LOT = 65
TFS = (1, 3, 5, 10, 15)


def _log(msg: str) -> None:
    print(f"[flawless] {msg}", file=sys.stderr, flush=True)


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


def simulate(
    bars: list[Bar],
    entry: list[bool],
    exit_: list[bool],
    *,
    side: str,
    strategy_id: str,
    sl: Optional[float],
    tp: Optional[float],
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
            "success_pct": None,
            "gross_pnl_inr": 0.0,
            "after_cost_pnl_inr": 0.0,
        }
    costed = [apply_round_trip(t) for t in trades]
    wins = sum(1 for t in trades if t.points > 0)
    gross = sum(t.points for t in trades) * LOT
    after = sum(t.points for t in costed) * LOT
    return {
        "trade_count": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate": wins / len(trades),
        "success_pct": round(100.0 * wins / len(trades), 1),
        "gross_pnl_inr": round(gross, 2),
        "after_cost_pnl_inr": round(after, 2),
    }


def watch_contracts(uni: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    pe = sorted(uni["itm_pe"], key=lambda x: x["strike"])
    ce = sorted(uni["itm_ce"], key=lambda x: -x["strike"])
    # 4 PE + 3 CE near spot — enough for table without 20× fetch wall
    return [("PE", x) for x in pe[:4]] + [("CE", x) for x in ce[:3]]


def main() -> int:
    root = repo_root()
    uni = json.loads((root / "data" / "recon" / "itm_strike_universe.json").read_text())
    client = DhanClient(load_settings())
    start = datetime(2026, 8, 1, 9, 15, tzinfo=IST)
    end = datetime(2026, 9, 12, 15, 30, tzinfo=IST)
    watches = watch_contracts(uni)
    grid = default_param_grid()

    cache: dict[str, list[Bar]] = {}
    for side, meta in watches:
        sid = str(meta["security_id"])
        _log(f"fetch {side} {meta['strike']} sid={sid}")
        cache[sid] = load_bars(client, sid, start, end)
        _log(f"  bars={len(cache[sid])}")
        time.sleep(0.25)

    rows: list[dict[str, Any]] = []
    for side, meta in watches:
        sid = str(meta["security_id"])
        bars_1m = cache.get(sid) or []
        if len(bars_1m) < 80:
            continue
        for tf in TFS:
            bars = bars_1m if tf == 1 else resample(bars_1m, tf)
            if len(bars) < 40:
                continue
            for params in grid:
                entry, exit_ = flawless_signals(bars, params)
                trades = simulate(
                    bars,
                    entry,
                    exit_,
                    side=side,
                    strategy_id=f"MIX-FLAWLESS-{params.version.upper()}",
                    sl=params.sl,
                    tp=params.tp,
                )
                sc = score(trades)
                rows.append(
                    {
                        "version": params.version,
                        "tf": f"{tf}m",
                        "tf_minutes": tf,
                        "side": side,
                        "strike": int(meta["strike"]),
                        "security_id": sid,
                        "params": params.label(),
                        "bb_length": params.bb_length,
                        "bb_mult": params.bb_mult,
                        "rsi_buy": params.rsi_buy,
                        "rsi_sell": params.rsi_sell,
                        "mfi_buy": params.mfi_buy,
                        "mfi_sell": params.mfi_sell,
                        "sl": params.sl,
                        "tp": params.tp,
                        "pine_default": params.label()
                        in {
                            FlawlessParams("v1", 20, 1.0, 42, 70).label(),
                            FlawlessParams(
                                "v2", 17, 1.0, 42, 76, sl=0.06604, tp=0.02328
                            ).label(),
                            FlawlessParams(
                                "v3",
                                20,
                                1.0,
                                42,
                                65,
                                60,
                                64,
                                sl=0.08882,
                                tp=0.02317,
                            ).label(),
                        },
                        **sc,
                    }
                )

    # Aggregate version × TF × params across contracts
    from collections import defaultdict

    bucket: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = (r["version"], r["tf"], r["params"])
        bucket[key].append(r)

    table: list[dict[str, Any]] = []
    for (version, tf, params), group in bucket.items():
        trades = sum(g["trade_count"] for g in group)
        wins = sum(g["wins"] for g in group)
        after = sum(g["after_cost_pnl_inr"] for g in group)
        gross = sum(g["gross_pnl_inr"] for g in group)
        pe_after = sum(g["after_cost_pnl_inr"] for g in group if g["side"] == "PE")
        ce_after = sum(g["after_cost_pnl_inr"] for g in group if g["side"] == "CE")
        table.append(
            {
                "version": version,
                "tf": tf,
                "params": params,
                "pine_default": group[0]["pine_default"],
                "contracts": len(group),
                "trade_count": trades,
                "wins": wins,
                "losses": trades - wins,
                "success_pct": round(100.0 * wins / trades, 1) if trades else None,
                "gross_pnl_inr": round(gross, 2),
                "after_cost_pnl_inr": round(after, 2),
                "avg_after_cost_per_contract": round(after / len(group), 2),
                "pe_after_cost_pnl_inr": round(pe_after, 2),
                "ce_after_cost_pnl_inr": round(ce_after, 2),
                "contracts_positive": sum(
                    1 for g in group if g["after_cost_pnl_inr"] > 0
                ),
            }
        )

    table.sort(
        key=lambda r: (r["after_cost_pnl_inr"], r["success_pct"] or 0), reverse=True
    )

    # Compact markdown-friendly top / by TF for Pine defaults
    pine_defaults = [r for r in table if r["pine_default"]]
    pine_defaults.sort(key=lambda r: (r["version"], r["tf_minutes"] if False else r["tf"]))
    # sort pine by version then tf minutes
    tf_order = {f"{t}m": t for t in TFS}
    pine_defaults.sort(key=lambda r: (r["version"], tf_order.get(r["tf"], 99)))

    best_by_tf: dict[str, dict[str, Any]] = {}
    for r in table:
        if r["trade_count"] <= 0:
            continue
        if r["tf"] not in best_by_tf:
            best_by_tf[r["tf"]] = r

    report = {
        "title": "Flawless Victory — ITM option premium multi-TF grid",
        "source": "Bunghole Flawless Victory Strategy (MPL-2.0 Pine v4 port)",
        "mode": "PAPER",
        "promotion": "NO_PROMOTE",
        "orders": "refused",
        "lot": LOT,
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "spot": uni["spot"],
        "expiry": uni["expiry"],
        "watch_contracts": [
            {"side": s, "strike": m["strike"], "security_id": str(m["security_id"])}
            for s, m in watches
        ],
        "timeframes": [f"{t}m" for t in TFS],
        "n_param_sets": len(grid),
        "n_result_rows": len(rows),
        "n_table_rows": len(table),
        "plain_english": {
            "v1": "Buy when close < BB lower (20,1) and RSI>42; sell when close > BB upper and RSI>70. No SL/TP.",
            "v2": "Same idea with BB(17,1), RSI sell>76, plus ~6.6% SL / ~2.3% TP.",
            "v3": "Buy BB lower + MFI<60; sell BB upper + RSI>65 + MFI>64; ~8.9% SL / ~2.3% TP.",
        },
        "pine_defaults_table": pine_defaults,
        "best_by_tf": best_by_tf,
        "top_20": table[:20],
        "bottom_10": table[-10:],
        "honesty": [
            "Option premium ≠ the crypto/FX chart this Pine was tuned on.",
            "Next-bar-open fills; TV strategy tester can differ.",
            "MFI needs volume — OPTIDX volume used; sparse zero-vol bars weaken MFI.",
            "Grid search = multiple-testing bias. NO_PROMOTE.",
            "After-cost uses HYPOTHESIS 1% RT slip.",
        ],
    }

    out = root / "data" / "recon" / "itm_flawless_victory.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    mock = root / "apps" / "web" / "public" / "mock" / "itm_flawless_victory.json"
    mock.parent.mkdir(parents=True, exist_ok=True)
    mock.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _log(f"wrote {out}")

    # stdout: founder tables
    print("=== PINE DEFAULTS (across watch contracts, 1 lot, after cost) ===")
    print(
        f"{'ver':4} {'tf':4} {'trades':>6} {'succ%':>6} {'after₹':>12} {'PE₹':>10} {'CE₹':>10} {'+ctr':>4}"
    )
    for r in pine_defaults:
        print(
            f"{r['version']:4} {r['tf']:4} {r['trade_count']:6d} "
            f"{str(r['success_pct']):>6} {r['after_cost_pnl_inr']:12.0f} "
            f"{r['pe_after_cost_pnl_inr']:10.0f} {r['ce_after_cost_pnl_inr']:10.0f} "
            f"{r['contracts_positive']:4d}/{r['contracts']}"
        )
    print("\n=== TOP 15 GRID (any version/TF/params) ===")
    print(
        f"{'ver':4} {'tf':4} {'trades':>6} {'succ%':>6} {'after₹':>12}  params"
    )
    for r in table[:15]:
        print(
            f"{r['version']:4} {r['tf']:4} {r['trade_count']:6d} "
            f"{str(r['success_pct']):>6} {r['after_cost_pnl_inr']:12.0f}  {r['params']}"
        )
    print("\n=== BEST PER TF ===")
    for tf in [f"{t}m" for t in TFS]:
        r = best_by_tf.get(tf)
        if not r:
            print(f"{tf}: no trades")
            continue
        print(
            f"{tf}: {r['version']} succ={r['success_pct']}% after₹={r['after_cost_pnl_inr']:.0f} "
            f"trades={r['trade_count']} | {r['params']}"
        )
    print(json.dumps({"path": str(out), "top_1": table[0] if table else None}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
