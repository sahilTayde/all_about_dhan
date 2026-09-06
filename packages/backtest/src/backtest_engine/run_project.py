"""PROJECT_MIX option books: MIX-MTF-TREND and MIX-CONFIRM-5M. NIFTY+SENSEX only."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.algos import (
    align_leans_to,
    and_same_side,
    macd_hist_side,
    strat_001_parent_leans,
    strat_003_leans,
)
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.fetch_rolling import fetch_rolling_range
from backtest_engine.option_sim import simulate_option_premium
from backtest_engine.resample import resample
from backtest_engine.run_option import STRIKE_005_ITM, _opt_tf, _row, _expiry_flag

IST = timezone(timedelta(hours=5, minutes=30))
UNIVERSE = ("NIFTY", "SENSEX")
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[project] {msg}", file=sys.stderr, flush=True)


def run_project_mixes(
    client: DhanClient, *, years: float = 5.0, interval: int = 1
) -> dict[str, Any]:
    books: list[dict] = []
    roll_meta: dict[str, Any] = {}
    index_meta: dict[str, Any] = {}
    for name in UNIVERSE:
        _, sid, seg, inst = INDEX_BY_NAME[name]
        _log(f"index 1m {name}")
        series = fetch_range(
            client,
            security_id=sid,
            exchange_segment=seg,
            instrument=inst,
            interval=1,
            years=years,
        )
        bars_1m = series.get("bars") or []
        bars_3m = resample(bars_1m, 3)
        leans_003 = strat_003_leans(bars_3m, equal_weight_vwap=True)
        parent, leans_001p = strat_001_parent_leans(bars_1m)
        gate_001 = align_leans_to(bars_3m, parent, leans_001p)
        leans_mtf = and_same_side(leans_003, gate_001)
        bars_5m = resample(bars_1m, 5)
        gate_5m = align_leans_to(bars_3m, bars_5m, macd_hist_side(bars_5m))
        leans_confirm = and_same_side(leans_003, gate_5m)
        index_meta[name] = {k: v for k, v in series.items() if k != "bars"}

        flag = _expiry_flag(name)
        fno_seg = "NSE_FNO" if name != "SENSEX" else "BSE_FNO"
        idx_sid = "13" if name == "NIFTY" else "51"
        _log(f"rolling {name} 005_ITM {flag}")
        ce = fetch_rolling_range(
            client,
            security_id=idx_sid,
            exchange_segment=fno_seg,
            strike=STRIKE_005_ITM["CE"],
            option_type="CALL",
            interval=interval,
            years=years,
            expiry_flag=flag,
        )
        if name == "NIFTY" and ce.get("bar_count", 0) < 200:
            flag = "MONTH"
            ce = fetch_rolling_range(
                client,
                security_id=idx_sid,
                exchange_segment=fno_seg,
                strike=STRIKE_005_ITM["CE"],
                option_type="CALL",
                interval=interval,
                years=years,
                expiry_flag=flag,
            )
        pe = fetch_rolling_range(
            client,
            security_id=idx_sid,
            exchange_segment=fno_seg,
            strike=STRIKE_005_ITM["PE"],
            option_type="PUT",
            interval=interval,
            years=years,
            expiry_flag=flag,
        )
        roll_meta[f"{name}/005_ITM"] = {
            "ce": {k: v for k, v in ce.items() if k != "bars"},
            "pe": {k: v for k, v in pe.items() if k != "bars"},
            "expiry_flag_used": flag,
        }
        ce_3 = _opt_tf(ce.get("bars") or [], 3)
        pe_3 = _opt_tf(pe.get("bars") or [], 3)
        extra = {
            "underlying": name,
            "tape": "OPTIDX_ROLLING",
            "strike_map": STRIKE_005_ITM,
            "origin": "PROJECT_MIX",
            "signal_tf": "3m_INDEX_resample",
            "not_dhan_derived": True,
        }
        _log(f"simulate {name} mtf={sum(1 for x in leans_mtf if x in ('CE','PE'))} confirm={sum(1 for x in leans_confirm if x in ('CE','PE'))}")
        books.append(
            _row(
                f"MIX-MTF-TREND/{name}/005_ITM",
                simulate_option_premium(
                    bars_3m,
                    leans_mtf,
                    ce_3,
                    pe_3,
                    strategy_id="MIX-MTF-TREND",
                    underlying=name,
                    use_009=True,
                    use_007_allow=None,
                    veto_sessions=None,
                ),
                {**extra, "filters": ["001_1h_parent", "009"], "not_attached": ["002", "006", "007", "008"]},
            )
        )
        books.append(
            _row(
                f"MIX-CONFIRM-5M/{name}/005_ITM",
                simulate_option_premium(
                    bars_3m,
                    leans_confirm,
                    ce_3,
                    pe_3,
                    strategy_id="MIX-CONFIRM-5M",
                    underlying=name,
                    use_009=True,
                    use_007_allow=None,
                    veto_sessions=None,
                ),
                {
                    **extra,
                    "filters": ["5m_MACD_HIST_sign", "009"],
                    "not_attached": ["002", "006", "007", "008", "5m_Supertrend"],
                },
            )
        )

    slim = [
        {
            "book_id": b.get("book_id"),
            "rating": b.get("rating"),
            "reason": b.get("reason"),
            "underlying": b.get("underlying"),
            "trade_count": b.get("trade_count"),
            "is": b.get("is"),
            "oos": b.get("oos"),
            "all": b.get("all"),
            "origin": b.get("origin"),
        }
        for b in books
    ]
    report = {
        "as_of_ist": datetime.now(IST).isoformat(),
        "years_requested": years,
        "option_interval": interval,
        "universe": list(UNIVERSE),
        "metrics_claimed": False,
        "research_ready_for_programming": False,
        "keep_current_strategy": True,
        "promote": False,
        "pnl_unit": "OPTION_PREMIUM_POINTS",
        "costs": "UNKNOWN",
        "news_filter": "DATA_INSUFFICIENT",
        "rolling_meta": roll_meta,
        "index_meta": index_meta,
        "books_summary": slim,
        "books": books,
        "note": (
            "PROJECT_MIX only. MIX-MTF-TREND = 003 AND 001 1h parent. "
            "MIX-CONFIRM-5M = 003 AND 5m MACD hist sign. 005 ITM. 009 flatten. "
            "Not DHAN-DERIVED. Not customer default. Not a promote."
        ),
    }
    out = repo_root() / "data" / "recon"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"BACKTEST_PROJECT_{datetime.now(IST).date().isoformat()}.json"
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    report["wrote"] = str(path)
    return report
