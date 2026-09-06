"""Rescore frozen 2y club books after hypothesis costs + expiry strip.

Does not retune grids. Does not invent STT. Does not promote.
True NORMAL is invalid until a news calendar exists.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.algos import run_strat_003
from backtest_engine.clocks import drop_dead_band
from backtest_engine.costs import DEFAULT_COST, apply_round_trip_many
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.fetch_rolling import fetch_rolling_range
from backtest_engine.futidx_continuous import fetch_listed_futidx
from backtest_engine.patterns import lean_gap
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.run_club import _cutoff_ts, _sim, frozen_club_leans
from backtest_engine.run_option import STRIKE_005_ITM, _expiry_flag, _opt_tf
from backtest_engine.sessions import (
    analog_gap_sessions,
    calendar_meta,
    filter_trades,
    last_session_of_iso_week,
    load_news_calendar,
    session_universe_from_bars,
)
from backtest_engine.simulate import Trade, trades_as_dicts

IST = timezone(timedelta(hours=5, minutes=30))
UNIVERSE = ("NIFTY", "SENSEX")
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[honest] {msg}", file=sys.stderr, flush=True)


def _decorate_cost(
    rating: dict,
    extra: dict,
    trades: list[Trade],
    *,
    cost_applied: bool,
) -> dict:
    rating.update(extra)
    rating["pnl_unit"] = "OPTION_PREMIUM_POINTS"
    rating["option_pnl"] = rating.get("all", {}).get("sum_pts")
    rating["trade_count"] = len(trades)
    rating["trade_sample"] = trades_as_dicts(trades[:6])
    rating["promote"] = False
    rating["validated"] = False
    rating["keep_current_strategy"] = True
    if cost_applied:
        rating["costs"] = DEFAULT_COST.name
        rating["expectancy_label"] = "AFTER_HYPOTHESIS_COST"
        rating["cost_model"] = DEFAULT_COST.as_dict()
        if rating.get("rating") == "CANDIDATE":
            rating["rating"] = "WEAK"
            rating["reason"] = (
                (rating.get("reason") or "")
                + " Hypothesis cost overlay — statutory UNKNOWN — capped at WEAK."
            )
    else:
        rating["costs"] = "UNKNOWN"
        rating["expectancy_label"] = "OPTIMISTIC"
    return rating


def _score_book(
    book_id: str,
    trades: list[Trade],
    extra: dict,
    *,
    cost_applied: bool,
) -> dict:
    rating = rate_trades(trades, book_id=book_id)
    return _decorate_cost(rating, extra, trades, cost_applied=cost_applied)


def run_honest(client: DhanClient, *, years: float = 5.0, interval: int = 1) -> dict[str, Any]:
    start_2y = _cutoff_ts(730)
    news_days, news_status = load_news_calendar()
    books: list[dict] = []
    session_meta: dict[str, Any] = {}

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
        dates = session_universe_from_bars(bars_3m)
        expiry_proxy = last_session_of_iso_week(dates)
        gap_sessions = analog_gap_sessions(dates, lean_gap(bars_3m), bars_3m)
        session_meta[name] = {
            **calendar_meta(news_status, len(expiry_proxy), len(news_days)),
            "gap_sessions_n": len(gap_sessions),
            "session_n": len(dates),
        }
        frozen = frozen_club_leans(bars_3m, start_2y=start_2y)
        for mix_id, leans in frozen.items():
            _log(f"sim {name} {mix_id}")
            two_y = [t for t in _sim(bars_3m, leans, ce_3, pe_3, mix_id, name) if t.entry_ts >= start_2y]
            after_cost = apply_round_trip_many(two_y, DEFAULT_COST)
            stripped = filter_trades(
                after_cost,
                expiry_proxy=expiry_proxy,
                news_days=news_days,
                news_status=news_status,
                gap_sessions=gap_sessions,
                mode="expiry_stripped",
            )
            score_sample = filter_trades(
                after_cost,
                expiry_proxy=expiry_proxy,
                news_days=news_days,
                news_status=news_status,
                gap_sessions=gap_sessions,
                mode="score_sample",
            )
            base_extra = {
                "underlying": name,
                "origin": "PROJECT_MIX",
                "strike_map": STRIKE_005_ITM,
                "clock": "FOUNDER_DEAD_BAND_0900_0930_1500_1530",
                "window": "730d",
                "nested_holdout": False,
                "retune": False,
            }
            books.append(
                _score_book(
                    f"{mix_id}/{name}/005_ITM/AFTER_COST",
                    after_cost,
                    {**base_extra, "sample": "ALL_DAYS_AFTER_HYPOTHESIS_COST"},
                    cost_applied=True,
                )
            )
            books.append(
                _score_book(
                    f"{mix_id}/{name}/005_ITM/EXPIRY_STRIPPED",
                    stripped,
                    {
                        **base_extra,
                        "sample": "EXPIRY_STRIPPED",
                        "session_kind": "UNKNOWN" if news_status == "DATA_INSUFFICIENT" else "NORMAL",
                        "news_filter": news_status,
                    },
                    cost_applied=True,
                )
            )
            books.append(
                _score_book(
                    f"{mix_id}/{name}/005_ITM/SCORE_SAMPLE",
                    score_sample,
                    {
                        **base_extra,
                        "sample": "SCORE_SAMPLE",
                        "news_filter": news_status,
                    },
                    cost_applied=True,
                )
            )

    _log("futidx continuous")
    fut = fetch_listed_futidx(client, years=years, interval=1)
    futidx_books: list[dict] = []
    futidx_meta: dict[str, Any] = {}
    for name, pack in (fut.get("by_name") or {}).items():
        bars_1m = drop_dead_band(pack.get("stitched_bars") or [])
        bars_3m = drop_dead_band(resample(bars_1m, 3)) if bars_1m else []
        trades = run_strat_003(
            bars_3m,
            underlying=name,
            equal_weight_vwap=False,
            strategy_id="STRAT-003",
        )
        rating = rate_trades(trades, book_id=f"STRAT-003/{name}/FUTIDX-STITCH-3m")
        rating.update(
            {
                "underlying": name,
                "tape": "FUTIDX_STITCH",
                "origin": "DHAN-DERIVED-003",
                "continuous_status": pack.get("status"),
                "span_days": pack.get("span_days"),
                "stitched_n": pack.get("stitched_n"),
                "contract_count": pack.get("contract_count"),
                "pnl_unit": "UNDERLYING_POINTS_PROXY",
                "option_pnl": None,
                "costs": "UNKNOWN",
                "promote": False,
                "validated": False,
                "trade_count": len(trades),
                "trade_sample": trades_as_dicts(trades[:6]),
            }
        )
        if pack.get("status") == "DATA_INSUFFICIENT":
            rating["rating"] = "DATA_INSUFFICIENT"
            rating["reason"] = (
                "Continuous FUTIDX history DATA_INSUFFICIENT "
                f"(span_days={pack.get('span_days')}, contracts={pack.get('contract_count')}). "
                "Spoken STRAT-003 stays on INDEX 3m resample until expired-month IDs exist."
            )
        futidx_books.append(rating)
        futidx_meta[name] = {k: v for k, v in pack.items() if k != "stitched_bars"}

    slim = [
        {
            "book_id": b.get("book_id"),
            "rating": b.get("rating"),
            "sample": b.get("sample"),
            "oos": b.get("oos"),
            "n": b.get("trade_count"),
        }
        for b in books
    ]
    report = {
        "as_of_ist": datetime.now(IST).isoformat(),
        "universe": list(UNIVERSE),
        "years_scored": 2,
        "metrics_claimed": False,
        "research_ready_for_programming": False,
        "keep_current_strategy": True,
        "promote": False,
        "retune": False,
        "cost_model": DEFAULT_COST.as_dict(),
        "session_meta": session_meta,
        "news_filter": news_status,
        "normal_only_valid": news_status != "DATA_INSUFFICIENT",
        "futidx_continuous": {
            "ok": fut.get("ok"),
            "error": fut.get("error"),
            "by_name": futidx_meta,
        },
        "note": (
            "Frozen club leans only — no grid retune. "
            "Hypothesis 1% each-way premium haircut; statutory UNKNOWN. "
            "EXPIRY_STRIPPED is not NORMAL. SCORE_SAMPLE empty without news calendar. "
            "Continuous FUTIDX stitch from live CSV only. Not a promote."
        ),
        "books_summary": slim,
        "books": books,
        "futidx_003": futidx_books,
    }
    out = repo_root() / "data" / "recon"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"BACKTEST_HONEST_{datetime.now(IST).date().isoformat()}.json"
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    report["wrote"] = str(path)
    return report
