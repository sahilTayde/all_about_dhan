"""2y club + annexure nested grid. Founder clock. Not a promote."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.algos import and_many, macd_hist_side
from backtest_engine.clocks import drop_dead_band
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.fetch_rolling import fetch_rolling_range
from backtest_engine.ml_leans import lean_ml_logit
from backtest_engine.option_sim import simulate_option_premium
from backtest_engine.patterns import (
    lean_bb_break,
    lean_donchian_n,
    lean_ema_cross,
    lean_engulf,
    lean_gap,
    lean_range_exp,
    lean_rsi_mr,
    lean_rsi_trend,
    lean_sma_cross,
)
from backtest_engine.rating import rate_split, rate_trades
from backtest_engine.resample import resample
from backtest_engine.run_option import STRIKE_005_ITM, _expiry_flag, _opt_tf, _row
from backtest_engine.simulate import Trade, trades_as_dicts

IST = timezone(timedelta(hours=5, minutes=30))
UNIVERSE = ("NIFTY", "SENSEX")
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}
# Nested: lock params on first 60% of the 2y window by time; score the last 40%.
TUNE_FRAC = 0.60


def _log(msg: str) -> None:
    print(f"[club] {msg}", file=sys.stderr, flush=True)


def _cutoff_ts(days: int) -> int:
    end = datetime.now(IST)
    return int((end - timedelta(days=days)).timestamp())


def _exp(trades: list[Trade]) -> tuple[float, float, int]:
    if not trades:
        return -1e9, 0.0, 0
    pts = [t.points for t in trades]
    wr = sum(1 for p in pts if p > 0) / len(pts)
    return sum(pts) / len(pts), wr, len(pts)


def _decorate(rating: dict, extra: dict, trades: list[Trade]) -> dict:
    rating.update(extra)
    rating["pnl_unit"] = "OPTION_PREMIUM_POINTS"
    rating["option_pnl"] = rating.get("all", {}).get("sum_pts")
    rating["trade_count"] = len(trades)
    rating["trade_sample"] = trades_as_dicts(trades[:6])
    rating["costs"] = "UNKNOWN"
    rating["expectancy_label"] = "OPTIMISTIC"
    rating["promote"] = False
    rating["validated"] = False
    if rating.get("rating") == "CANDIDATE":
        rating["rating"] = "WEAK"
        rating["reason"] = (
            (rating.get("reason") or "")
            + " Costs UNKNOWN — capped at WEAK / UNVALIDATED. Not a promote."
        )
    return rating


def frozen_club_leans(bars_3m, *, start_2y: int) -> dict[str, list[str]]:
    """Named WEAK-club + annexure leans. No nested grid. Do not retune after wr."""
    engulf = lean_engulf(bars_3m)
    gap = lean_gap(bars_3m)
    xr = lean_range_exp(bars_3m)
    ml = lean_ml_logit(bars_3m, train_end_ts=start_2y)
    ml_xr = and_many([ml, xr])
    return {
        "MIX-CLUB-EG": and_many([engulf, gap]),
        "MIX-CLUB-ER": and_many([engulf, xr]),
        "MIX-CLUB-GR": and_many([gap, xr]),
        "MIX-CLUB-EGR": and_many([engulf, gap, xr]),
        "MIX-CLUB-EXR": and_many([engulf, ml_xr]),
        "MIX-CLUB-GXR": and_many([gap, ml_xr]),
        "MIX-RSI-MR": lean_rsi_mr(bars_3m, 30, 70),
        "MIX-RSI-2575": lean_rsi_mr(bars_3m, 25, 75),
        "MIX-RSI-TREND": lean_rsi_trend(bars_3m, 50),
        "MIX-MACD-HIST": macd_hist_side(bars_3m),
        "MIX-SMA-20-50": lean_sma_cross(bars_3m, 20, 50),
        "MIX-EMA-10-50": lean_ema_cross(bars_3m, 10, 50),
        "MIX-EMA-20-100": lean_ema_cross(bars_3m, 20, 100),
    }


def _sim(bars_3m, leans, ce_3, pe_3, mix_id: str, name: str) -> list[Trade]:
    return simulate_option_premium(
        bars_3m,
        leans,
        ce_3,
        pe_3,
        strategy_id=mix_id,
        underlying=name,
        use_009=False,
        skip_open=False,
        session_end_flatten=True,
    )


def _pick_grid(
    *,
    variants: list[tuple[str, list[str]]],
    sim: Callable[[list[str]], list[Trade]],
    tune_ts: int,
) -> tuple[str, list[str], dict[str, Any]]:
    best_name = variants[0][0]
    best_leans = variants[0][1]
    best_exp = -1e9
    trail = []
    for label, leans in variants:
        trades = sim(leans)
        is_rows = [t for t in trades if t.entry_ts < tune_ts]
        exp, wr, n = _exp(is_rows)
        trail.append({"id": label, "is_n": n, "is_wr": round(wr, 4), "is_exp": round(exp, 4)})
        if n < 20:
            continue
        if exp > best_exp:
            best_exp = exp
            best_name = label
            best_leans = leans
    return best_name, best_leans, {"picked": best_name, "is_exp": best_exp, "grid": trail}


def run_club(client: DhanClient, *, years: float = 5.0, interval: int = 1) -> dict[str, Any]:
    """Load 5y cache for ML train + fills; score last 730d only."""
    start_2y = _cutoff_ts(730)
    span = int(datetime.now(IST).timestamp()) - start_2y
    tune_ts = start_2y + int(span * TUNE_FRAC)
    books: list[dict] = []
    for name in UNIVERSE:
        _, sid, seg, inst = INDEX_BY_NAME[name]
        _log(f"index {name}")
        series = fetch_range(
            client,
            security_id=sid,
            exchange_segment=seg,
            instrument=inst,
            interval=1,
            years=years,
        )
        bars_1m = drop_dead_band(series.get("bars") or [])
        bars_3m = drop_dead_band(resample(bars_1m, 3))
        flag = _expiry_flag(name)
        fno = "BSE_FNO" if name == "SENSEX" else "NSE_FNO"
        idx_sid = "51" if name == "SENSEX" else "13"
        ce = fetch_rolling_range(
            client,
            security_id=idx_sid,
            exchange_segment=fno,
            strike=STRIKE_005_ITM["CE"],
            option_type="CALL",
            interval=interval,
            years=years,
            expiry_flag=flag,
        )
        pe = fetch_rolling_range(
            client,
            security_id=idx_sid,
            exchange_segment=fno,
            strike=STRIKE_005_ITM["PE"],
            option_type="PUT",
            interval=interval,
            years=years,
            expiry_flag=flag,
        )
        ce_3 = drop_dead_band(_opt_tf(drop_dead_band(ce.get("bars") or []), 3))
        pe_3 = drop_dead_band(_opt_tf(drop_dead_band(pe.get("bars") or []), 3))
        frozen: dict[str, list[str]] = frozen_club_leans(bars_3m, start_2y=start_2y)

        def sim(leans: list[str], mix_id: str = "tmp") -> list[Trade]:
            return _sim(bars_3m, leans, ce_3, pe_3, mix_id, name)

        grids = [
            (
                "MIX-GRID-RSI",
                [
                    (f"RSI_MR_{lo}_{hi}", lean_rsi_mr(bars_3m, lo, hi))
                    for lo, hi in ((20, 80), (25, 75), (30, 70))
                ],
            ),
            (
                "MIX-GRID-DONCH",
                [(f"DONCH_{n}", lean_donchian_n(bars_3m, n)) for n in (10, 20, 40)],
            ),
            (
                "MIX-GRID-BB",
                [(f"BB_k{k}", lean_bb_break(bars_3m, 20, k)) for k in (1.5, 2.0, 2.5)],
            ),
            (
                "MIX-GRID-EMA",
                [
                    (f"EMA_{f}_{s}", lean_ema_cross(bars_3m, f, s))
                    for f, s in ((10, 50), (20, 50), (20, 100))
                ],
            ),
        ]
        picked_meta: dict[str, Any] = {}
        for gid, variants in grids:
            _log(f"grid {name} {gid}")
            label, leans, meta = _pick_grid(
                variants=variants,
                sim=lambda ln, gid=gid: sim(ln, gid),
                tune_ts=tune_ts,
            )
            frozen[gid] = leans
            picked_meta[gid] = meta
            picked_meta[gid]["locked"] = label

        for mix_id, leans in frozen.items():
            _log(f"sim {name} {mix_id}")
            trades_all = sim(leans, mix_id)
            holdout = [t for t in trades_all if t.entry_ts >= tune_ts]
            two_y = [t for t in trades_all if t.entry_ts >= start_2y]
            extra = {
                "underlying": name,
                "origin": "PROJECT_MIX",
                "strike_map": STRIKE_005_ITM,
                "multiple_testing": True,
                "clock": "FOUNDER_DEAD_BAND_0900_0930_1500_1530",
                "window": "730d",
                "nested_holdout": mix_id.startswith("MIX-GRID-"),
                "grid": picked_meta.get(mix_id),
            }
            if mix_id.startswith("MIX-GRID-"):
                is_rows = [t for t in trades_all if start_2y <= t.entry_ts < tune_ts]
                oos_rows = [t for t in trades_all if t.entry_ts >= tune_ts]
                rating = rate_split(
                    is_rows, oos_rows, book_id=f"{mix_id}/{name}/005_ITM"
                )
                row = _decorate(rating, extra, oos_rows)
                row["holdout_n"] = len(oos_rows)
                row["tune_ts"] = tune_ts
            else:
                row = _row(f"{mix_id}/{name}/005_ITM", two_y, extra)
            books.append(row)

    slim = [
        {
            "book_id": b.get("book_id"),
            "rating": b.get("rating"),
            "oos": b.get("oos"),
            "n": b.get("trade_count"),
            "grid": b.get("grid"),
            "nested_holdout": b.get("nested_holdout"),
        }
        for b in books
    ]
    report = {
        "as_of_ist": datetime.now(IST).isoformat(),
        "universe": list(UNIVERSE),
        "years_scored": 2,
        "tune_frac": TUNE_FRAC,
        "discarded": [
            "MIX-ORB-* (empty under dead band)",
            "MIX-ML-LOGIT (55% wr, exp<0)",
            "MIX-PDH-PDL / MIX-CPR-BIAS / MIX-NR7-BRK (extreme 2y wr)",
        ],
        "metrics_claimed": False,
        "research_ready_for_programming": False,
        "keep_current_strategy": True,
        "promote": False,
        "multiple_testing": True,
        "costs": "UNKNOWN",
        "note": (
            "2y only. Club WEAK survivors (ENGULF/GAP/RANGE-EXP/ML-XR). "
            "Annexure RSI/SMA/EMA/MACD computed from OHLC (no HQ series REST). "
            "GRID books: params locked on first 60% of 2y by expectancy, scored on last 40%. "
            "Not a promote. Not DHAN-DERIVED."
        ),
        "books_summary": slim,
        "books": books,
    }
    out = repo_root() / "data" / "recon"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"BACKTEST_CLUB_{datetime.now(IST).date().isoformat()}.json"
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    report["wrote"] = str(path)
    return report
