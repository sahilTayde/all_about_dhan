"""Scan 20 WEB/PATTERN MIX books on expanding windows. NIFTY+SENSEX option premium."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.algos import and_same_side
from backtest_engine.clocks import drop_dead_band
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.fetch_rolling import fetch_rolling_range
from backtest_engine.ml_leans import lean_ml_logit
from backtest_engine.option_sim import simulate_option_premium
from backtest_engine.patterns import catalog_leans, lean_range_exp
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.run_option import STRIKE_005_ITM, _expiry_flag, _opt_tf, _row
from backtest_engine.simulate import Trade

IST = timezone(timedelta(hours=5, minutes=30))
UNIVERSE = ("NIFTY", "SENSEX")
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}
WINDOWS_DAYS = (30, 90, 180, 365, 730)
FIVE_Y_DAYS = 5 * 365
# Frozen from MIX_SCAN_2026-09-03 — do not retag after wr.
WEB_DERIVED = frozenset(
    {
        "MIX-ORB-15",
        "MIX-ORB-VWAP",
        "MIX-PDH-PDL",
        "MIX-CPR-BIAS",
        "MIX-CPR-ORB",
        "MIX-NR7-BRK",
        "MIX-PIVOT-R1",
        "MIX-GAP",
    }
)


def _log(msg: str) -> None:
    print(f"[scan] {msg}", file=sys.stderr, flush=True)


def _cutoff_ts(days: int) -> int:
    end = datetime.now(IST)
    start = end - timedelta(days=days)
    return int(start.timestamp())


def _slice_trades(trades: list[Trade], start_ts: int) -> list[Trade]:
    return [t for t in trades if t.entry_ts >= start_ts]


def _window_row(book_id: str, trades: list[Trade], days: int) -> dict[str, Any]:
    rating = rate_trades(trades, book_id=f"{book_id}/{days}d")
    n = len(trades)
    oos_n = (rating.get("oos") or {}).get("n") or 0
    if days <= 90:
        rating["window_role"] = "SCREEN"
        rating["rating"] = "SCREEN"
        rating["reason"] = (
            f"{days}d screen only (OOS n={oos_n}). Not FAIL/PASS. Not a promote."
        )
    rating["window_days"] = days
    rating["trade_count"] = n
    rating["promote"] = False
    rating["validated"] = False
    if rating.get("rating") == "CANDIDATE":
        rating["rating"] = "WEAK"
        rating["reason"] = (rating.get("reason") or "") + " Costs UNKNOWN — not CANDIDATE."
    return rating


def _pass_730(row: dict) -> bool:
    if row.get("window_days") != 730:
        return False
    if row.get("rating") in ("SCREEN", "DATA_INSUFFICIENT"):
        return False
    oos = row.get("oos") or {}
    wr = oos.get("win_rate")
    exp = oos.get("expectancy_pts")
    n = oos.get("n") or 0
    return n >= 30 and wr is not None and wr >= 0.45 and exp is not None and exp > 0


def run_scan(
    client: DhanClient, *, years: float = 5.0, interval: int = 1
) -> dict[str, Any]:
    start_2y = _cutoff_ts(730)
    books: list[dict] = []
    survivors: list[str] = []
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
        _log(f"rolling {name}")
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
        ce_1 = drop_dead_band(ce.get("bars") or [])
        pe_1 = drop_dead_band(pe.get("bars") or [])
        ce_3 = drop_dead_band(_opt_tf(ce_1, 3))
        pe_3 = drop_dead_band(_opt_tf(pe_1, 3))
        catalog = catalog_leans(bars_1m, bars_3m)
        train_end = _cutoff_ts(730)
        _log(f"ml logit {name} train_end={train_end}")
        ml_leans = lean_ml_logit(bars_3m, train_end_ts=train_end)
        catalog["MIX-ML-LOGIT"] = (ml_leans, False)
        catalog["MIX-ML-LOGIT-XR"] = (
            and_same_side(ml_leans, lean_range_exp(bars_3m)),
            False,
        )
        for mix_id, (leans, _skip_open_flag) in catalog.items():
            _log(f"sim {name} {mix_id}")
            trades_all = simulate_option_premium(
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
            extra = {
                "underlying": name,
                "origin": (
                    "PROJECT_MIX"
                    if mix_id.startswith("MIX-ML-")
                    else ("WEB-DERIVED" if mix_id in WEB_DERIVED else "PROJECT_MIX")
                ),
                "strike_map": STRIKE_005_ITM,
                "multiple_testing": True,
                "clock": "FOUNDER_DEAD_BAND_0900_0930_1500_1530",
            }
            windows = []
            row_730 = None
            for days in WINDOWS_DAYS:
                cut = _cutoff_ts(days)
                wtrades = _slice_trades(trades_all, cut)
                wr = _window_row(f"{mix_id}/{name}", wtrades, days)
                windows.append(wr)
                if days == 730:
                    row_730 = wr
            five = None
            if row_730 and _pass_730(row_730):
                survivors.append(f"{mix_id}/{name}")
                five = _window_row(f"{mix_id}/{name}", trades_all, FIVE_Y_DAYS)
                five["window_role"] = "CONFIRM_5Y"
            books.append(
                {
                    **_row(
                        f"{mix_id}/{name}/005_ITM",
                        _slice_trades(trades_all, start_2y),
                        extra,
                    ),
                    "windows": windows,
                    "five_year": five,
                    "skip_open": False,
                    "session_end_flatten": True,
                }
            )

    slim = []
    for b in books:
        w730 = next((w for w in b.get("windows") or [] if w.get("window_days") == 730), {})
        slim.append(
            {
                "book_id": b.get("book_id"),
                "rating_2y": b.get("rating"),
                "oos_2y": b.get("oos"),
                "n_2y": b.get("trade_count"),
                "w730_rating": w730.get("rating"),
                "w730_oos": w730.get("oos"),
                "five_year": None
                if not b.get("five_year")
                else {
                    "rating": b["five_year"].get("rating"),
                    "oos": b["five_year"].get("oos"),
                },
                "origin": b.get("origin"),
            }
        )
    report = {
        "as_of_ist": datetime.now(IST).isoformat(),
        "universe": list(UNIVERSE),
        "windows_days": list(WINDOWS_DAYS),
        "survivors_730": survivors,
        "metrics_claimed": False,
        "research_ready_for_programming": False,
        "keep_current_strategy": True,
        "promote": False,
        "multiple_testing": True,
        "costs": "UNKNOWN",
        "clock": "drop 09:00-09:30 and 15:00-15:30 IST; flatten session end (before CAS)",
        "note": (
            "22 MIX books (20 WEB/PATTERN + MIX-ML-LOGIT + MIX-ML-LOGIT-XR). "
            "Founder dead band. 30d/90d SCREEN only. "
            "5y only if 730d OOS wr>=45% and exp>0. Not a promote. Not DHAN-DERIVED. "
            "ML trains on INDEX direction before 730d cutoff; never on option premium."
        ),
        "books_summary": slim,
        "books": books,
    }
    out = repo_root() / "data" / "recon"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"BACKTEST_SCAN_CLOCK_{datetime.now(IST).date().isoformat()}.json"
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    report["wrote"] = str(path)
    return report
